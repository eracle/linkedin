# linkedin/workflow.py
import csv
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from typing import Dict, Optional

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from linkedin.campaigns.load import campaigns
from linkedin.conf import DATA_DIR
from linkedin.navigation.login import get_resources_with_state_management

logger = logging.getLogger(__name__)


def compute_csv_hash(csv_path: Path) -> str:
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)
    urls = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        import csv
        reader = csv.DictReader(f)
        if "url" not in reader.fieldnames:
            raise ValueError("CSV missing 'url' column")
        for row in reader:
            url = row["url"].strip().rstrip("/")
            if url:
                if not url.endswith("/"):
                    url += "/"
                urls.append(url.lower())
    urls = sorted(set(urls))
    content = "\n".join(urls).encode()
    return hashlib.sha256(content).hexdigest()[:12]


def get_campaign_db_path(handle: str, campaign_name: str, csv_path: Path) -> tuple[Any, str]:
    csv_hash = compute_csv_hash(csv_path)
    safe_campaign = campaign_name.replace(" ", "_").lower()
    db_path = DATA_DIR / f"linkedin_{handle}+{safe_campaign}+{csv_hash}.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path, csv_hash


def _normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url.endswith("/"):
        url += "/"
    return url.lower()


def load_profiles_from_csv(csv_path: Path) -> list[dict]:
    """Pure stdlib CSV loader – fast, clean, no dependencies"""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    seen = set()
    profiles = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "url" not in reader.fieldnames:
            raise ValueError("CSV must contain 'url' column")

        for row in reader:
            raw_url = row["url"]
            if not raw_url:
                continue
            normalized = _normalize_url(raw_url)
            if normalized not in seen:
                seen.add(normalized)
                profiles.append({"linkedin_url": normalized})

    logger.info(f"Loaded {len(profiles)} unique profiles from {csv_path.name}")
    return profiles


class LinkedInCampaignEngine:
    """
    One instance = One fully independent campaign run
    (account + campaign + input CSV)
    """

    def __init__(
            self,
            handle: str,
            campaign_name: str,
            input_csv: str | Path,
    ):
        self.handle = handle
        self.campaign_name = campaign_name
        self.input_csv = Path(input_csv).expanduser().resolve()

        self.campaign = None
        self.scheduler: Optional[BackgroundScheduler] = None
        self.resources = None  # Shared browser context
        self.db_path, self.csv_hash = get_campaign_db_path(handle, campaign_name, self.input_csv)

        self.stats = {
            "total_profiles": 0,
            "completed": 0,
            "failed": 0,
            "started_at": datetime.now().isoformat(),
            "csv_hash": self.csv_hash,
        }

        logger.info(f"Engine initialized → DB: {self.db_path.name}")

    # ------------------------------------------------------------------
    # One shared browser context – created once
    # ------------------------------------------------------------------
    def _init_browser(self) -> None:
        if self.resources is None:
            logger.info(f"Logging in once for account: {self.handle}")
            self.resources = get_resources_with_state_management(
                handle=self.handle,
                use_state=True,
                force_login=True,
            )

    # ------------------------------------------------------------------
    # Core per-profile job – runs sequentially
    # ------------------------------------------------------------------
    def _process_profile_job(self, profile: Dict[str, Any], state: Dict[str, Any]) -> None:
        step_index = state.get("step_index", 0)
        if step_index >= len(self.campaign.steps):
            logger.info(f"Completed: {profile['linkedin_url']}")
            self.stats["completed"] += 1
            return

        step = self.campaign.steps[step_index]
        context = {"resources": self.resources}

        try:
            logger.info(
                f"[{self.handle}] {profile['linkedin_url']} → "
                f"Step {step_index + 1}/{len(self.campaign.steps)}: {step.type.upper()}"
            )

            if step.type == "scrape":
                enriched = step.handler(context, profile)
                profile.update(enriched)

            elif step.type == "action":
                step.handler(context, profile)

            elif step.type == "condition":
                if step.handler(context, profile):
                    logger.info("Condition met → continuing")
                else:
                    delay = step.check_interval or timedelta(hours=6)
                    self.scheduler.add_job(
                        self._process_profile_job,
                        trigger="date",
                        run_date=datetime.now() + delay,
                        id=state["job_id"],
                        replace_existing=True,
                        kwargs={"profile": profile, "state": state},
                    )
                    logger.info(f"Condition not met → retry in {delay}")
                    return

            # Advance
            state["step_index"] = step_index + 1
            self.scheduler.add_job(
                self._process_profile_job,
                trigger="date",
                run_date=datetime.now(),
                id=state["job_id"],
                replace_existing=True,
                kwargs={"profile": profile, "state": state},
            )

        except Exception as e:
            logger.error(f"FAILED: {profile['linkedin_url']} | {e}", exc_info=True)
            self.stats["failed"] += 1

    # ------------------------------------------------------------------
    # Schedule initial jobs (first run only)
    # ------------------------------------------------------------------
    def _schedule_initial_jobs(self, profiles: list[dict]) -> None:
        """Create one persistent job per profile – only on first run"""
        for profile in profiles:
            job_id = f"{self.campaign_name}::{profile['linkedin_url']}"
            state = {
                "job_id": job_id,
                "step_index": 0,
                "created_at": datetime.now().isoformat(),
            }

            self.scheduler.add_job(
                func=self._process_profile_job,
                trigger="date",
                run_date=datetime.now(),
                id=job_id,
                replace_existing=False,
                kwargs={
                    "profile": profile.copy(),
                    "state": state,
                },
            )

        logger.info(f"Scheduled {len(profiles)} initial profile jobs")

    # ------------------------------------------------------------------
    # Public: Start or resume
    # ------------------------------------------------------------------
    def start(self) -> "LinkedInCampaignEngine":
        self.campaign = campaigns.get(self.campaign_name)
        if not self.campaign:
            raise ValueError(
                f"Campaign '{self.campaign_name}' not found. Available: {list(campaigns._registry.keys())}")

        # Optional: also set as attribute for muscle memory
        setattr(campaigns, "current", self.campaign)  # now you can do campaigns.current

        self._init_browser()

        self.scheduler = BackgroundScheduler(
            jobstores={"default": SQLAlchemyJobStore(url=f"sqlite:///{self.db_path}")},
            executors={"default": ThreadPoolExecutor(max_workers=1)},
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": None,
            },
        )
        self.scheduler.start()
        logger.info("Scheduler started (single-threaded)")

        if self.db_path.exists():
            logger.info("DB found → Campaign resumed")
        else:
            profiles = load_profiles_from_csv(self.input_csv)
            self.stats["total_profiles"] = len(profiles)
            self._schedule_initial_jobs(profiles)

        return self

    # ------------------------------------------------------------------
    # Control & monitoring
    # ------------------------------------------------------------------
    def stop(self) -> None:
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Engine stopped gracefully")

    def status(self) -> dict:
        jobs = self.scheduler.get_jobs() if self.scheduler else []
        pending = len([j for j in jobs if j.next_run_time])
        return {
            "account": self.handle,
            "campaign": self.campaign_name,
            "db_file": self.db_path.name,
            "csv_hash": self.csv_hash,
            "pending_jobs": pending,
            "completed": self.stats["completed"],
            "failed": self.stats["failed"],
            "total": self.stats["total_profiles"],
        }


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import time

    # Forcefully reset and configure logging to ensure reliability
    root_logger = logging.getLogger()
    root_logger.handlers = []  # Clear any existing handlers to avoid conflicts
    logging.basicConfig(
        level=logging.DEBUG,  # Set to DEBUG for more logs; change to INFO if too verbose
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    engine = LinkedInCampaignEngine(
        handle="eracle",
        campaign_name="linked_in_connect_follow_up",
        input_csv="./assets/inputs/urls.csv",
    ).start()

    logger.info("Campaign running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(60)
            print(f"Status → {engine.status()}")
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        engine.stop()
        logger.info("Bye.")
