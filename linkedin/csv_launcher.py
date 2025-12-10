# linkedin/csv_launcher.py
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import pandas as pd

from linkedin.campaigns.connect_follow_up import process_profile_row, CAMPAIGN_NAME, INPUT_CSV_PATH
from linkedin.conf import get_first_active_account
from linkedin.sessions.registry import AccountSessionRegistry

logger = logging.getLogger(__name__)


def load_profiles_urls_from_csv(csv_path: Path | str) -> List[str]:
    csv_path = Path(csv_path)
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    possible_cols = ["url", "linkedin_url", "profile_url"]
    url_column = next(
        (col for col in df.columns if col.lower() in [c.lower() for c in possible_cols]),
        None,
    )

    if url_column is None:
        raise ValueError(f"No URL column found. Available: {list(df.columns)}")

    urls = (
        df[url_column]
        .astype(str)
        .str.strip()
        .replace({"nan": None, "<NA>": None})
        .dropna()
        .drop_duplicates()  # Remove duplicates (preserves order)
    )

    logger.debug(f"First 10 rows of {csv_path.name}:\n{urls.head(10).to_string(index=False)}")

    logger.info(f"Loaded {len(urls):,} pristine LinkedIn profile URLs")
    return urls.tolist()


def launch_from_csv(
        handle: str,
        csv_path: Path | str = INPUT_CSV_PATH,
        campaign_name: str = CAMPAIGN_NAME,
) -> List[Dict[str, Any]]:
    logger.info(f"Launching campaign '{campaign_name}' → running as @{handle} | CSV: {csv_path}")

    profiles = load_profiles_urls_from_csv(csv_path)
    logger.info(f"Loaded {len(profiles):,} profiles from CSV – ready for battle!")

    _ = AccountSessionRegistry.get_or_create_from_path(
        handle=handle,
        campaign_name=campaign_name,
        csv_path=csv_path,
    )

    results: List[Dict[str, Any]] = []

    for idx, profile_url in enumerate(profiles, start=1):
        result = process_profile_row(
            profile_url=profile_url,
            handle=handle,
            campaign_name=campaign_name,
        )
        results.append(result)
        status = result.get('status', 'unknown')

        if status == "completed":
            status_emoji = "\033[1;92mCOMPLETED\033[0m"  # bold green
        elif status == "waiting_for_acceptance":
            status_emoji = "\033[93mPENDING\033[0m"  # yellow
        else:
            status_emoji = "\033[91mERROR\033[0m"  # red

        logger.info(f"\033[32m[{idx}]\033[0m Done → @{handle} | {status_emoji} {status} |")

    # Summary
    successful = sum(1 for r in results if r.get("status") == "completed")
    waiting = sum(1 for r in results if r.get("status") == "waiting_for_acceptance")
    errors = len(results) - successful - waiting

    logger.info(
        f"\033[1;36mCampaign '{campaign_name}' completed!\033[0m "
        f"Completed: {successful:,} | Waiting: {waiting:,} | Errors: {errors}"
    )

    return results


def launch_connect_follow_up_campaign(
        handle: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    One-liner to run the connect → follow-up campaign.

    If handle is not provided, automatically uses the first active account
    from accounts.secrets.yaml — perfect for quick tests and notebooks!
    """
    if handle is None:
        handle = get_first_active_account()
        if handle is None:
            raise RuntimeError(
                "No handle provided and no active accounts found in assets/accounts.secrets.yaml. "
                "Please either pass a handle explicitly or add at least one active account."
            )
        logger.info(f"No handle chosen → auto-picking the boss account: @{handle}")

    return launch_from_csv(handle=handle)