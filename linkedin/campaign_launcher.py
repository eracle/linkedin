# linkedin/campaign_launcher.py
import logging
from datetime import timedelta
from pathlib import Path
from typing import List

from temporalio.client import Client as TemporalClient, Client

from linkedin.account_session import AccountSessionRegistry
from linkedin.csv_utils import load_profile_urls_from_csv
from linkedin.db.engine import Database
from linkedin.db.engine import (
    has_campaign_run,
    mark_campaign_run,
    update_campaign_stats,
    get_campaign_short_id,
    get_campaign_stats,
)

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Defaults
# ----------------------------------------------------------------------
DEFAULT_HANDLE = "eracle"
DEFAULT_CAMPAIGN_NAME = "linked_in_connect_follow_up"
DEFAULT_INPUT_CSV = Path("./assets/inputs/urls.csv")


async def launch_campaign(
        handle: str | None = None,
        campaign_name: str | None = None,
        input_csv_path: Path | str | None = None,
        temporal_client: TemporalClient | None = None,
) -> None:
    """
    One-liner to start or resume a LinkedIn connect + follow-up campaign.
    """
    handle = handle or DEFAULT_HANDLE
    campaign_name = campaign_name or DEFAULT_CAMPAIGN_NAME
    input_csv_path = Path(input_csv_path or DEFAULT_INPUT_CSV)

    # ------------------------------------------------------------------
    # 1. Hash + Session
    # ------------------------------------------------------------------
    input_hash = Database.hash_file(input_csv_path)
    logger.info(f"CSV hash: {input_hash}")

    session = AccountSessionRegistry.get_or_create(
        handle=handle,
        campaign_name=campaign_name,
        csv_hash=input_hash,
        input_csv=input_csv_path,
    )

    db = session.db

    # ------------------------------------------------------------------
    # 2. Check if campaign already exists
    # ------------------------------------------------------------------
    with db.get_session() as s:
        if has_campaign_run(s, campaign_name, handle, input_hash):
            short_id = get_campaign_short_id(s, campaign_name, handle, input_hash)
            stats = get_campaign_stats(s, campaign_name, handle, input_hash) or {}
            logger.info(
                f"Campaign already running → resuming\n"
                f"   Campaign ID: {short_id}\n"
                f"   Handle     : {handle}\n"
                f"   CSV        : {input_csv_path}\n"
                f"   Stats      : {stats.get('enriched', 0)} enriched | "
                f"{stats.get('connect_sent', 0)} connects | "
                f"{stats.get('accepted', 0)} accepted | "
                f"{stats.get('completed', 0)} done"
            )
            return

        # ------------------------------------------------------------------
        # 3. First time → load URLs and start workflows
        # ------------------------------------------------------------------
        logger.info("New campaign detected – loading URLs...")
        profile_urls: List[str] = load_profile_urls_from_csv(input_csv_path)
        total = len(profile_urls)
        logger.info(f"Loaded {total} unique profile URLs")

        short_id = mark_campaign_run(s, campaign_name, handle, input_hash)
        update_campaign_stats(s, campaign_name, handle, input_hash, total_profiles=total)

    # ------------------------------------------------------------------
    # 4. Start Temporal workflows
    # ------------------------------------------------------------------
    if temporal_client is None:
        temporal_client = await Client.connect("localhost:7233")

    workflow_id_prefix = f"{campaign_name}::{handle}::{short_id}"
    started = 0

    for idx, url in enumerate(profile_urls, start=1):
        workflow_id = f"{workflow_id_prefix}::profile_{idx:06d}"

        await temporal_client.start_workflow(
            campaign_name,
            url,  # single argument expected by your workflow
            id=workflow_id,
            task_queue="linkedin-queue",  # change if needed
            execution_timeout=timedelta(days=30),
        )
        started += 1
        if started % 100 == 0 or started == total:
            logger.info(f"Started {started}/{total} workflows...")

    logger.info(
        f"SUCCESS! All {total} workflows queued.\n"
        f"   Campaign ID : {short_id}\n"
        f"   Prefix      : {workflow_id_prefix}\n"
        f"   Monitor with: tctl workflow list --query 'WorkflowType=\"{campaign_name}\"'"
    )
