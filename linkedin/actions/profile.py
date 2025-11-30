# linkedin/actions/profile.py
import logging
from pathlib import Path
from typing import Dict, Any

from linkedin.navigation.utils import wait
from linkedin.sessions import AccountSessionRegistry, SessionKey  # ← added SessionKey
from ..api.client import PlaywrightLinkedinAPI

logger = logging.getLogger(__name__)


def enrich_profile(key: SessionKey, profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    SCRAPE STEP handler

    Args:
        key: SessionKey identifying the persistent browser session
        profile: Must contain "linkedin_url"

    Returns:
        Same profile dict, enriched with full LinkedIn data
    """
    linkedin_url = profile["linkedin_url"]

    # ← only this block changed
    session = AccountSessionRegistry.get_or_create(
        handle=key.handle,
        campaign_name=key.campaign_name,
        csv_hash=key.csv_hash,
    )
    resources = session.resources

    # ──────────────────────────────
    wait(resources)
    api = PlaywrightLinkedinAPI(resources=resources)

    profile_data, raw_json = api.get_profile(profile_url=linkedin_url)

    # Merge everything
    enriched = {
        "linkedin_url": linkedin_url,
        **profile_data,
    }

    full_name = profile_data.get("full_name") or profile_data.get("name") or "Unknown"
    logger.info(f"Profile enriched: {full_name} – {linkedin_url}")

    return enriched


if __name__ == "__main__":
    import sys

    root_logger = logging.getLogger()
    root_logger.handlers = []
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) != 2:
        print("Usage: python -m linkedin.actions.profile <handle>")
        sys.exit(1)

    handle = sys.argv[1]

    # ← only this part changed
    key = SessionKey.make(
        handle=handle,
        campaign_name="test_profile",
        csv_path=Path("dummy.csv"),
    )

    test_profile = {"linkedin_url": "https://www.linkedin.com/in/williamhgates/"}

    enriched = enrich_profile(key, test_profile)

    print(f"Enriched profile for {enriched.get('full_name', 'Unknown')}")
