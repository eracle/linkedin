# linkedin/actions/profile.py
import logging
from typing import Dict, Any

from ..api.client import PlaywrightLinkedinAPI

logger = logging.getLogger(__name__)


def enrich_profile(context: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    SCRAPE STEP handler

    Args:
        context: Must contain "resources" (Playwright browser context + cookies)
        profile: Must contain "linkedin_url"

    Returns:
        Same profile dict, enriched with full LinkedIn data
    """
    linkedin_url = profile["linkedin_url"]
    resources = context["resources"]

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
    from linkedin.navigation.login import get_resources_with_state_management

    # Forcefully reset and configure logging to ensure reliability
    root_logger = logging.getLogger()
    root_logger.handlers = []  # Clear any existing handlers to avoid conflicts
    logging.basicConfig(
        level=logging.DEBUG,  # Set to DEBUG for more logs; change to INFO if too verbose
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    if len(sys.argv) != 2:
        print("Usage: python -m linkedin.actions.profile <handle>")
        sys.exit(1)
    handle = sys.argv[1]
    resources = get_resources_with_state_management(handle, use_state=True, force_login=False)
    context = dict(resources=resources)

    test_url = "https://www.linkedin.com/in/williamhgates/"
    profile = {"linkedin_url": test_url}

    enriched = enrich_profile(context, profile)

    # Cleanup
    resources.context.close()
    resources.browser.close()
    resources.playwright.stop()
