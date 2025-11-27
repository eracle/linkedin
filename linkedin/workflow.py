# linkedin/workflow.py
import csv
import hashlib
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from linkedin.automation import AutomationRegistry
from linkedin.campaigns import campaigns
from linkedin.conf import DATA_DIR

logger = logging.getLogger(__name__)


def compute_csv_hash(csv_path: Path) -> str:
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)
    hasher = hashlib.sha256()
    with open(csv_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()[:12]


def load_profiles_from_csv(csv_path: Path) -> list[dict]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    seen = set()
    profiles = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "url" not in reader.fieldnames:
            raise ValueError("CSV must contain 'url' column")
        for row in reader:
            url = row["url"].strip().rstrip("/")
            if url and url.lower() not in seen:
                seen.add(url.lower())
                profiles.append({"linkedin_url": url + "/" if not url.endswith("/") else url})
    logger.info(f"Loaded {len(profiles)} unique profiles from {csv_path.name}")
    return profiles


# ----------------------------------------------------------------------
# Core Engine
# ----------------------------------------------------------------------
class LinkedInCampaignEngine:
    def __init__(self, handle: str, campaign_name: str, input_csv: str | Path):
        self.handle = handle
        self.campaign_name = campaign_name
        self.input_csv = Path(input_csv).expanduser().resolve()

        self.campaign = campaigns.get(campaign_name)
        if not self.campaign:
            available = ", ".join(campaigns._registry.keys())
            raise ValueError(f"Campaign '{campaign_name}' not found. Available: {available}")

        self.csv_hash = compute_csv_hash(self.input_csv)
        self.db_path = DATA_DIR / f"campaign_{handle}+{campaign_name}+{self.csv_hash}.db"

        output_csv = self.campaign.settings.get(
            "output_csv",
            f"./assets/output/enriched_{campaign_name}+{self.csv_hash}.csv"
        )
        self.automation = AutomationRegistry.create_or_get(
            handle=handle,
            campaign_name=campaign_name,
            csv_hash=self.csv_hash,
            input_csv=self.input_csv,
            output_csv_template=output_csv,
        )

        self.scheduler: Optional[BackgroundScheduler] = None
        self.stats = {"completed": 0, "failed": 0}

    def _process_profile_job(self, profile: dict, state: dict):
        step_idx = state.get("step_index", 0)
        if step_idx >= len(self.campaign.steps):
            self.automation.append_to_csv(profile)
            self.stats["completed"] += 1
            logger.info(f"COMPLETED {profile.get('full_name', profile['linkedin_url'])}")
            return

        step = self.campaign.steps[step_idx]
        method_name = step.handler

        try:
            logger.info(
                f"[{self.handle}] {profile['linkedin_url']} → Step {step_idx + 1}/{len(self.campaign.steps)}: {method_name}"
            )

            # Resolve method at runtime from singleton
            method = getattr(self.automation, method_name)

            if step.type == "condition":
                accepted = method(profile, step.config)
                if accepted:
                    state["step_index"] += 1
                else:
                    delay = step.check_interval or timedelta(hours=6)
                    self.scheduler.add_job(
                        self._process_profile_job,
                        trigger="date",
                        run_date=datetime.now() + delay,
                        id=state["job_id"],
                        replace_existing=True,
                        kwargs={"profile": profile.copy(), "state": state},
                    )
                    logger.info(f"Waiting {delay} → retry")
                    return

            elif step.type == "scrape":
                enriched = method(profile)
                profile.update(enriched)

            else:  # action
                method(profile, step.config)

            # Always advance after action/scrape
            state["step_index"] += 1
            self.scheduler.add_job(
                self._process_profile_job,
                trigger="date",
                run_date=datetime.now(),
                id=state["job_id"],
                replace_existing=True,
                kwargs={"profile": profile.copy(), "state": state},
            )

        except Exception as e:
            logger.error(f"FAILED {profile['linkedin_url']}", exc_info=True)
            self.stats["failed"] += 1

    def start(self) -> "LinkedInCampaignEngine":
        resuming = self.db_path.exists()

        self.scheduler = BackgroundScheduler(
            jobstores={"default": SQLAlchemyJobStore(url=f"sqlite:///{self.db_path}")},
            executors={"default": ThreadPoolExecutor(1)},
            job_defaults={"coalesce": True, "max_instances": 1},
        )
        self.scheduler.start()

        if not resuming:
            profiles = load_profiles_from_csv(self.input_csv)
            for profile in profiles:
                job_id = f"{self.automation.key()}::{hash(profile['linkedin_url'])}"
                self.scheduler.add_job(
                    self._process_profile_job,
                    trigger="date",
                    run_date=datetime.now(),
                    id=job_id,
                    replace_existing=False,
                    kwargs={
                        "profile": profile.copy(),
                        "state": {"job_id": job_id, "step_index": 0},
                    },
                )
            logger.info(f"Scheduled {len(profiles)} new profiles")
        else:
            restored = len(self.scheduler.get_jobs())
            logger.info(f"Resumed campaign — {restored} jobs restored from DB")

        return self

    def stop(self):
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")

    def status(self) -> dict:
        jobs = self.scheduler.get_jobs() if self.scheduler else []
        pending = len([j for j in jobs if j.next_run_time])
        return {
            "account": self.handle,
            "campaign": self.campaign_name,
            "output_csv": str(self.automation._output_path),
            "pending": pending,
            "completed": self.stats["completed"],
            "failed": self.stats["failed"],
            "total": pending + self.stats["completed"] + self.stats["failed"],
        }


# ----------------------------------------------------------------------
# Convenience wrapper
# ----------------------------------------------------------------------
def start_or_resume_campaign(handle: str, campaign_name: str, input_csv: str | Path):
    engine = LinkedInCampaignEngine(handle, campaign_name, input_csv).start()
    return engine


# ----------------------------------------------------------------------
# CLI — run with: python -m linkedin.workflow
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import logging

    logging.getLogger().handlers.clear()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s │ %(levelname)-8s │ %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        engine = start_or_resume_campaign(
            handle="eracle",  # ← change to your handle
            campaign_name="linked_in_connect_follow_up",
            input_csv="./assets/inputs/urls.csv",
        )

        print("\nLinkedIn Campaign Engine STARTED")
        print(f"   Account  : {engine.handle}")
        print(f"   Campaign : {engine.campaign_name}")
        print(f"   Output   : {engine.automation._output_path.name}")
        print(f"   DB       : {engine.db_path.name}")
        print("   Press Ctrl+C to stop\n")

        while True:
            time.sleep(60)
            s = engine.status()
            print(
                f"Pending: {s['pending']:<4} │ "
                f"Done: {s['completed']:<4} │ "
                f"Failed: {s['failed']:<4} │ "
                f"Total: {s['total']:<4} │ "
                f"CSV → {s['output_csv']}"
            )

    except KeyboardInterrupt:
        print("\n\nShutting down gracefully...")
        engine.stop()
        print("Goodbye!")

    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        raise
