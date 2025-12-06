# linkedin/navigation/utils.py
import logging
import random
import time
from collections import namedtuple
from typing import Callable

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

# Central delay configuration
HUMAN_DELAY_MIN = 1.5
HUMAN_DELAY_MAX = 2.5


def human_delay(min_sec: float = HUMAN_DELAY_MIN, max_sec: float = HUMAN_DELAY_MAX) -> None:
    """Pure human-like random delay."""
    delay = random.uniform(min_sec, max_sec)
    logger.info(f"Pausing for {delay:.2f} seconds.")
    time.sleep(delay)


PlaywrightResources = namedtuple(
    'PlaywrightResources', ['page', 'context', 'browser', 'playwright']
)


def wait(resources: PlaywrightResources, min_sec: float = HUMAN_DELAY_MIN, max_sec: float = HUMAN_DELAY_MAX) -> None:
    """Legacy wrapper: human delay + wait for page load."""
    human_delay(min_sec, max_sec)
    resources.page.wait_for_load_state("load")
    # resources.page.wait_for_load_state("domcontentloaded")

from urllib.parse import unquote
def navigate_and_verify(
        resources: PlaywrightResources,
        action: Callable[[], None],
        expected_url_pattern: str,
        timeout: int = 5_000,
        error_message: str = "Navigation verification failed",
):
    page = resources.page

    try:
        action()
        page.wait_for_url(
            lambda url: expected_url_pattern in unquote(url),
            timeout=timeout,
        )
    except PlaywrightTimeoutError:
        # ignoring the exception here
        # I will check for url matching down below
        pass

    wait(resources)

    page_url = unquote(page.url)
    if expected_url_pattern not in page_url:
        raise RuntimeError(f"{error_message}: {expected_url_pattern} not in '{page_url}'")

    logger.info("Navigation OK → %s", page.url)
