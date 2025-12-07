# linkedin/navigation/login.py
import logging
from pathlib import Path

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

from linkedin.conf import get_account_config
from linkedin.navigation.utils import wait, goto_page
from linkedin.sessions.registry import SessionKey, AccountSessionRegistry

logger = logging.getLogger(__name__)

LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"

SELECTORS = {
    "email": 'input#username',
    "password": 'input#password',
    "submit": 'button[type="submit"]',
}


def playwright_login(session: "AccountSession"):
    page = session.page
    config = get_account_config(session.handle)
    logger.info("Starting fresh LinkedIn login for %s", session.handle)

    goto_page(
        session,
        action=lambda: page.goto(LINKEDIN_LOGIN_URL),
        expected_url_pattern="/login",
        error_message="Failed to load login page",
    )

    page.locator(SELECTORS["email"]).type(config["username"], delay=80)
    wait(session)
    page.locator(SELECTORS["password"]).type(config["password"], delay=80)
    wait(session)

    goto_page(
        session,
        action=lambda: page.locator(SELECTORS["submit"]).click(),
        expected_url_pattern="/feed",
        timeout=40_000,
        error_message="Login failed – no redirect to feed",
    )


def build_playwright(storage_state=None):
    logger.debug("Launching Playwright")
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False, slow_mo=200)
    context = browser.new_context(storage_state=storage_state)
    Stealth().apply_stealth_sync(context)
    page = context.new_page()
    return page, context, browser, playwright


def init_playwright_session(session: "AccountSession", handle: str):
    logger.info("Setting up browser for handle: %s", handle)
    config = get_account_config(handle)
    state_file = Path(config["cookie_file"])

    storage_state = str(state_file) if state_file.exists() else None
    if storage_state:
        logger.info("Loading saved cookies from: %s", state_file)

    page, context, browser, playwright = build_playwright(storage_state=storage_state)

    if not storage_state:
        playwright_login(session)
        state_file.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(state_file))
        logger.info("Login successful – session saved to %s", state_file)
    else:
        goto_page(
            session,
            action=lambda: page.goto(LINKEDIN_FEED_URL),
            expected_url_pattern="/feed",
            timeout=30_000,
            error_message="Saved session invalid",
        )

    page.wait_for_load_state("load")
    logger.info("Browser ready and authenticated!")
    return page, context, browser, playwright


if __name__ == "__main__":
    import sys

    from linkedin.campaigns.connect_follow_up import INPUT_CSV_PATH

    logging.getLogger().handlers.clear()
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s │ %(levelname)-8s │ %(message)s',
        datefmt="%H:%M:%S",
    )

    if len(sys.argv) != 2:
        print("Usage: python -m linkedin.navigation.login <handle>")
        sys.exit(1)

    handle = sys.argv[1]

    key = SessionKey.make(
        handle=handle,
        campaign_name="test_message",
        csv_path=INPUT_CSV_PATH,
    )

    session = AccountSessionRegistry.get_or_create_from_path(
        handle=handle,
        campaign_name="test_message",
        csv_path=INPUT_CSV_PATH,
    )

    session.ensure_browser()

    page, context, browser, playwright = init_playwright_session(session=session, handle=handle)
    print("Logged in! Close browser manually.")
    page.pause()
