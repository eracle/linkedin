# linkedin/actions/connect.py
import logging
import random
import time
from typing import Dict, Any

from linkedin.actions.login import PlaywrightResources, get_resources_with_state_management
from linkedin.actions.navigation import navigate_and_verify

logger = logging.getLogger(__name__)


def connect(linkedin_url: str, params: Dict[str, Any]):
    """Sends a connection request to a profile."""
    print(f"ACTION: connect for {linkedin_url} with params: {params}")
    pass


def wait(
        resources: PlaywrightResources,
        min_sleep: float = 0.5,
        max_sleep: float = 4.0
):
    """Introduces a random sleep to simulate human-like behavior and avoid detection, after waiting for page load."""
    time.sleep(random.uniform(min_sleep, max_sleep))
    resources.page.wait_for_load_state("load")


def send_connection_request(
        resources,
        profile,
):
    """Navigates to a LinkedIn profile and sends a connection request with customizable parameters."""
    # Navigate to the profile URL
    resources.page.goto(profile["linkedin_url"])
    wait(resources)  # Random sleep after navigation

    # Click the 'More' button on the profile page
    visible_button = resources.page.locator('button[id$="profile-overflow-action"]:visible').first
    visible_button.click()

    # Wait for the dropdown to load
    resources.page.wait_for_load_state("load")
    wait(resources)  # Random sleep after navigation

    # Locate and click the visible div with aria-label ending in "to connect"
    connect_div_locator = 'div[aria-label$="to connect"]:visible'
    connect_div = resources.page.locator(connect_div_locator).first
    connect_div.click()

    # Wait for the dropdown to load
    resources.page.wait_for_load_state("load")
    wait(resources)  # Random sleep after navigation

    # Locate and click the visible button with aria-label "Add a note"
    add_a_note_locator = 'button[aria-label$="Add a note"]:visible'
    add_a_note_div = resources.page.locator(add_a_note_locator).first
    add_a_note_div.click()

    # Wait for the dropdown to load
    resources.page.wait_for_load_state("load")
    wait(resources)  # Random sleep after navigation

    # Locate the visible textarea and type the message
    message_locator = 'textarea[name$="message"]:visible'
    message_div = resources.page.locator(message_locator).first
    message_div.type("Salve!")

    # Wait for stability
    resources.page.wait_for_load_state("load")
    wait(resources)  # Random sleep after navigation

    # Locate and click the visible button to send invitation
    send_button_locator = 'button[aria-label$="Send invitation"]:visible'
    send_button_div = resources.page.locator(send_button_locator).first
    send_button_div.click()
    wait(resources)  # Random sleep after navigation


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
        resources.page.wait_for_load_state('load')

        logger.info(f"Navigating directly to profile: {linkedin_url}")
        navigate_and_verify(
            resources,
            action=lambda: resources.page.goto(linkedin_url),
            expected_url_pattern=linkedin_id,
            error_message="Failed to navigate directly to the target profile"
        )

        # Directly navigate and send connection request
        send_connection_request(resources, target_profile)

        logger.info("send_connection_request function executed successfully.")
        logger.info(f"Final URL: {resources.page.url}")

    except Exception as e:
        logger.error(f"An unexpected error occurred during the test: {e}")
    finally:
        if resources:
            logger.info("Cleaning up Playwright resources.")
            resources.context.close()
            resources.browser.close()
            resources.playwright.stop()
