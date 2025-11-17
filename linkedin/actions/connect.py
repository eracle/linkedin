import random
import time
from typing import Dict, Any

from linkedin.actions.login import PlaywrightResources


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
