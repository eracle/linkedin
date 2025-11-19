# linkedin/actions/connect.py
import logging
import random
import time
from enum import Enum
from typing import Dict, Any

from linkedin.actions.login import PlaywrightResources, get_resources_with_state_management
from linkedin.actions.navigation import navigate_and_verify

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    CONNECTED = "connected"
    PENDING = "pending"
    NOT_CONNECTED = "not_connected"
    UNKNOWN = "unknown"


def connect(linkedin_url: str, params: Dict[str, Any]):
    """Sends a connection request to a profile."""
    print(f"ACTION: connect for {linkedin_url} with params: {params}")
    pass


def wait(
        resources: PlaywrightResources,
        min_sleep: float = 1,
        max_sleep: float = 3,
):
    """Introduces a random sleep to simulate human-like behavior and avoid detection, after waiting for page load."""
    time.sleep(random.uniform(min_sleep, max_sleep))
    resources.page.wait_for_load_state("load")

def get_connection_status(
        resources: PlaywrightResources,
        profile: Dict[str, Any],
) -> ConnectionStatus:
    """Checks the connection status of a LinkedIn profile."""
    # 1. Pending – very reliable, text is almost always in English ("Pending") even on localized UIs
    if resources.page.locator('button[aria-label*="Pending"]:visible').count() > 0:
        return ConnectionStatus.PENDING

    # 2. Already connected – distance badge is present and starts with "1"
    #     Works for English ("1st"), Italian/Spanish/Portuguese ("1°"), French ("1er"), etc.
    dist_locator = resources.page.locator('span[class^="distance-badge"]:visible')
    if dist_locator.count() > 0:
        badge_text = dist_locator.first.inner_text().strip()
        if badge_text.startswith("1"):
            return ConnectionStatus.CONNECTED

    # 3. Can send a request – direct "Invite … to connect" button exists
    if resources.page.locator('button[aria-label*="Invite"]:visible').count() > 0:
        return ConnectionStatus.NOT_CONNECTED

    # 4. Fallback
    return ConnectionStatus.UNKNOWN


def _perform_send_invitation(
        resources: PlaywrightResources,
        message: str,
):
    """Performs the actual steps to send the invitation after status check."""

    # Wait for the dropdown to load
    wait(resources)

    # Try direct connect button first
    direct_connect_locator = 'button[aria-label*="Invite"]:visible'
    direct_connect = resources.page.locator(direct_connect_locator)
    if direct_connect.count() > 0:
        direct_connect.first.click()
    else:
        # Click the 'More' button
        more_button = resources.page.locator('button[id$="profile-overflow-action"]:visible').first
        more_button.click()

        # Wait for the dropdown to load
        wait(resources)  # Random sleep

        # Locate and click the connect div
        connect_div_locator = 'div[aria-label$="to connect"]:visible'
        connect_div = resources.page.locator(connect_div_locator).first
        connect_div.click()
    # After initiating connect, wait for popup
    wait(resources)  # Random sleep

    # Locate and click the "Add a note" button
    add_a_note_locator = 'button[aria-label$="Add a note"]:visible'
    add_a_note_div = resources.page.locator(add_a_note_locator).first
    add_a_note_div.click()

    # Wait for the input to appear
    wait(resources)  # Random sleep

    # Locate the textarea and type the message
    message_locator = 'textarea[name$="message"]:visible'
    message_div = resources.page.locator(message_locator).first
    message_div.type(message)

    # Wait for stability

    wait(resources)  # Random sleep

    # Locate and click the send button
    send_button_locator = 'button[aria-label$="Send invitation"]:visible'
    send_button_div = resources.page.locator(send_button_locator).first
    send_button_div.click()
    wait(resources)  # Random sleep after send


def send_connection_request(
        resources: PlaywrightResources,
        profile: Dict[str, Any],
) -> ConnectionStatus:
    """Navigates to a LinkedIn profile, checks status, and sends a connection request if not connected or pending."""
    # Get current status
    status = get_connection_status(resources, profile)

    skip_statuses = {
        ConnectionStatus.CONNECTED: ("info", "Already connected. Skipping send."),
        ConnectionStatus.PENDING: ("info", "Connection request is already pending. Skipping send."),
        ConnectionStatus.UNKNOWN: ("warning", "Unknown connection status. Skipping send.")
    }

    if status in skip_statuses:
        log_level, message = skip_statuses[status]
        logger_func = logger.warning if log_level == "warning" else logger.info
        logger_func(message)
        return status

    # If not connected, proceed to send
    _perform_send_invitation(resources, message="Hello there")

    # Assume success, return pending
    return ConnectionStatus.PENDING


if __name__ == "__main__":
    # Forcefully reset and configure logging to ensure reliability
    root_logger = logging.getLogger()
    root_logger.handlers = []  # Clear any existing handlers to avoid conflicts
    logging.basicConfig(
        level=logging.DEBUG,  # Set to DEBUG for more logs; change to INFO if too verbose
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Example profile data for testing
    target_profile = {
        "full_name": "Bill Gates",
        "linkedin_url": "https://www.linkedin.com/in/williamhgates/",
        "public_id": "williamhgates",
    }
    linkedin_url = target_profile.get("linkedin_url")
    linkedin_id = target_profile.get("public_id")

    resources = None
    try:
        # Get resources with state management
        resources = get_resources_with_state_management(use_state=True, force_login=False)

        # Wait a bit after setup to observe
        wait(resources)

        logger.info(f"Navigating directly to profile: {linkedin_url}")
        navigate_and_verify(
            resources,
            action=lambda: resources.page.goto(linkedin_url),
            expected_url_pattern=linkedin_id,
            error_message="Failed to navigate directly to the target profile"
        )

        # Directly navigate and send connection request
        status = send_connection_request(resources, target_profile)
        logger.info(f"send_connection_request executed with status: {status.value}")

        logger.info(f"Final URL: {resources.page.url}")

    except Exception as e:
        logger.error(f"An unexpected error occurred during the test: {e}")
    finally:
        if resources:
            logger.info("Cleaning up Playwright resources.")
            resources.context.close()
            resources.browser.close()
            resources.playwright.stop()
