# linkedin/workflow.py
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from .campaigns import load_campaigns, ParsedCampaign, ExecutableStep
from .database import db_manager


logger = logging.getLogger(__name__)


class LinkedInWorkflowEngine:
    def __init__(self, db_url: str = "sqlite:///linkedin.db"):
        self.db_url = db_url
        self.scheduler: Optional[BackgroundScheduler] = None
        self.campaigns: List[ParsedCampaign] = []

    def _init_scheduler(self) -> None:
        """Initialize persistent APScheduler with SQLAlchemy job store."""
        jobstores = {"default": SQLAlchemyJobStore(url=self.db_url)}
        executors = {"default": ThreadPoolExecutor(max_workers=10)}
        job_defaults = {"coalesce": False, "max_instances": 3}

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
        )
        self.scheduler.start()
        logger.info("APScheduler started with persistence")

    def start_campaign(self, campaign: ParsedCampaign, start_from_step: int = 0) -> None:
        """Launch a campaign from the beginning (or a specific step)."""
        logger.info(f"Launching campaign: {campaign.name}")
        self.execute_step(campaign=campaign, profile=None, step_index=start_from_step)

    def execute_step(
        self,
        campaign: ParsedCampaign,
        profile: Optional[Dict[str, Any]],
        step_index: int,
    ) -> None:
        """Core recursive engine: executes one step for one profile (or globally for scrape steps)."""
        if step_index >= len(campaign.steps):
            if profile:
                logger.info(f"Workflow completed for {profile.get('linkedin_url')}")
            return

        step: ExecutableStep = campaign.steps[step_index]

        # ------------------------------------------------------------------
        # 1. Scrape step → produces many profiles → fan-out
        # ------------------------------------------------------------------
        if step.type == "scrape":
            enriched_profiles = step.execute(context={}, profile=None)
            if not enriched_profiles:
                logger.warning(f"Scrape step '{step.name}' returned no profiles → campaign stopped")
                return

            for prof in enriched_profiles:
                self.execute_step(campaign, profile=prof, step_index=step_index + 1)
            return

        # ------------------------------------------------------------------
        # 2. Action step → needs a profile
        # ------------------------------------------------------------------
        if step.type == "action":
            if not profile:
                logger.error("Action step received no profile")
                return

            step.execute(context={}, profile=profile)
            self.execute_step(campaign, profile, step_index + 1)
            return

        # ------------------------------------------------------------------
        # 3. Condition step → polling with backoff/timeout
        # ------------------------------------------------------------------
        if step.type == "condition":
            if not profile:
                logger.error("Condition step received no profile")
                return

            url = profile["linkedin_url"]
            job_id = f"cond_{campaign.name}_{step_index}_{abs(hash(url)) & 0xFFFFFF}"

            self.scheduler.add_job(
                self.check_condition_job,
                trigger="date",
                run_date=datetime.now() + timedelta(seconds=15),  # first check quickly
                id=job_id,
                replace_existing=True,
                kwargs={
                    "campaign_name": campaign.name,
                    "profile_url": url,
                    "step_index": step_index,
                    "attempt": 1,
                },
            )
            logger.info(f"Condition scheduled for {url} (job {job_id})")

    def check_condition_job(
        self,
        campaign_name: str,
        profile_url: str,
        step_index: int,
        attempt: int,
    ) -> None:
        """Job run by APScheduler to poll a condition."""
        campaign = next((c for c in self.campaigns if c.name == campaign_name), None)
        if not campaign:
            logger.error(f"Campaign '{campaign_name}' not found during condition check")
            return

        step: ExecutableStep = campaign.steps[step_index]
        profile = {"linkedin_url": profile_url}

        condition_met: bool = step.execute(context={}, profile=profile)

        if condition_met:
            logger.info(f"Condition met for {profile_url} after {attempt} attempt(s)")
            self.execute_step(campaign, profile=profile, step_index=step_index + 1)
            return

        # Reschedule next check
        interval = step.check_interval or timedelta(hours=6)
        next_check = datetime.now() + interval

        # Timeout logic
        if step.timeout and (attempt * interval) >= step.timeout:
            logger.warning(f"Timeout reached for {profile_url} — abandoning")
            return

        job_id = f"cond_{campaign_name}_{step_index}_{abs(hash(profile_url)) & 0xFFFFFF}"
        self.scheduler.add_job(
            self.check_condition_job,
            trigger="date",
            run_date=next_check,
            id=job_id,
            replace_existing=True,
            kwargs={
                "campaign_name": campaign_name,
                "profile_url": profile_url,
                "step_index": step_index,
                "attempt": attempt + 1,
            },
        )
        logger.info(f"Condition not met → rescheduling in {interval} (attempt {attempt + 1})")

    # ----------------------------------------------------------------------
    # Lifecycle methods
    # ----------------------------------------------------------------------
    def start(self) -> None:
        """Initialize everything and start the first campaign."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%H:%M:%S",
        )

        logger.info("Initializing database…")
        db_manager.init_db(self.db_url)
        db_manager.create_tables()

        logger.info("Loading campaigns…")
        self.campaigns = load_campaigns()
        if not self.campaigns:
            logger.error("No campaigns found in config → exiting")
            return

        self._init_scheduler()

        # Start the first campaign (you can easily modify to start multiple)
        self.start_campaign(self.campaigns[0])

        logger.info("LinkedIn Workflow Engine is running! Press Ctrl+C to stop.")

        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            self.shutdown()

    def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("Shutting down engine…")
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=True)
        logger.info("Engine stopped. Bye!")


# ----------------------------------------------------------------------
# Convenience entry-point (keeps backward compatibility)
# ----------------------------------------------------------------------
def main(db_url: str = "sqlite:///linkedin.db") -> None:
    engine = LinkedInWorkflowEngine(db_url=db_url)
    engine.start()


if __name__ == "__main__":
    main()