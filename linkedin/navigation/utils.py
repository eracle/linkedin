# linkedin/navigation/utils.py
import logging
import random
import time
from urllib.parse import unquote, urlparse, urljoin

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

# Central delay configuration
HUMAN_DELAY_MIN = 1.5
HUMAN_DELAY_MAX = 2.5


def human_delay():
    delay = random.uniform(HUMAN_DELAY_MIN, HUMAN_DELAY_MAX)
    logger.info(f"Pause: {delay:.2f}s")
    time.sleep(delay)


def wait(session):
    human_delay()
    session.page.wait_for_load_state("load")


def goto_page(session: "AccountSession",
              action,
              expected_url_pattern: str,
              timeout: int = 10_000,
              error_message: str = ""):
    from linkedin.db.engine import add_profile_urls
    page = session.page
    action()
    if not page:
        return

    try:
        page.wait_for_url(lambda url: expected_url_pattern in unquote(url), timeout=timeout)
    except PlaywrightTimeoutError:
        pass  # we still continue and check URL below

    wait(session)

    page_url = unquote(page.url)
    if expected_url_pattern not in page_url:
        raise RuntimeError(f"{error_message}: {expected_url_pattern} not in '{page_url}'")

    logger.info("Navigated to %s", page.url)

    try:
        urls = _extract_in_urls(session)
        add_profile_urls(session, list(urls))
    except Exception as e:
        logger.error(f"Failed to extract/save profile URLs after navigation: {e}", exc_info=True)

def _extract_in_urls(session):
    page = session.page
    urls = set()
    for link in page.locator('a[href*="/in/"]').all():
        href = link.get_attribute("href")
        if href and "/in/" in href:
            # resolves relative + protocol-relative URLs
            full_url = urljoin(page.url, href.strip())
            clean = urlparse(full_url)._replace(query="", fragment="").geturl()
            urls.add(clean)
    logger.info(f"Extracted {len(urls)} unique /in/ profiles")
    return urls


def url_to_public_id(url: str) -> str:
    """
    Convert any LinkedIn profile URL → public_identifier (e.g. 'john-doe-1a2b3c4d')

    Examples:
      "https://www.linkedin.com/in/john-doe-1a2b3c4d/?originalSubdomain=fr" → "john-doe-1a2b3c4d"
      "https://linkedin.com/in/alice/" → "alice"
      "http://linkedin.com/in/bob-123/" → "bob-123"
    """
    if not url:
        return ""

    parsed = urlparse(url.strip().lower())
    if not parsed.path:
        return ""

    # Remove leading '/in/' and trailing slash
    path = parsed.path.strip("/")
    if not path.startswith("in/"):
        return ""

    public_id = path[3:]  # strip the "in/"
    if public_id.endswith("/"):
        public_id = public_id[:-1]

    return unquote(public_id)


def public_id_to_url(public_id: str) -> str:
    """
    Convert public_identifier back to a clean LinkedIn profile URL.

    You can choose www or not — both work, www is slightly more common.
    """
    if not public_id:
        return ""

    public_id = public_id.strip("/")
    scheme = "https"
    domain = "linkedin.com"
    return f"{scheme}://{domain}/in/{public_id}/"
