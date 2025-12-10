# campaigns/connect_follow_up.py
import logging
from pathlib import Path

from linkedin.db.profiles import get_profile_state, set_profile_state, get_profile
from linkedin.navigation.enums import ProfileState, MessageStatus
from linkedin.navigation.exceptions import TerminalStateError
from linkedin.sessions.registry import SessionKey

logger = logging.getLogger(__name__)

# ———————————————————————————————— USER CONFIGURATION ————————————————————————————————
CAMPAIGN_NAME = "connect_follow_up"
INPUT_CSV_PATH = Path("./assets/inputs/urls.csv")

# ———————————————————————————————— Template Config ————————————————————————————————
# CONNECT_TEMPLATE_FILE = "./assets/templates/connect_notes/leader.j2"
# CONNECT_TEMPLATE_TYPE = "jinja"

FOLLOWUP_TEMPLATE_FILE = "./assets/templates/prompts/followup.j2"
FOLLOWUP_TEMPLATE_TYPE = "ai_prompt"


# ———————————————————————————————— Core Logic ————————————————————————————————
def process_profile_row(
        key: SessionKey,
        session: "AccountSession",
        public_identifier: str,
):
    from linkedin.actions.connect import send_connection_request
    from linkedin.actions.message import send_follow_up_message
    from linkedin.actions.profile import scrape_profile
    from linkedin.navigation.enums import ConnectionStatus

    old_state = ProfileState(get_profile_state(session, public_identifier) or ProfileState.DISCOVERED)
    profile = get_profile(session, public_identifier).profile
    new_state = None

    match old_state:
        case ProfileState.COMPLETED | ProfileState.FAILED:
            return None

        case ProfileState.DISCOVERED:
            profile = scrape_profile(key=key, profile=profile)
            new_state = ProfileState.FAILED.value if profile is None else ProfileState.ENRICHED.value

        case ProfileState.ENRICHED:
            status = send_connection_request(key=key, profile=profile)
            new_state = ProfileState.CONNECTED.value if status == ConnectionStatus.CONNECTED else ProfileState.ENRICHED.value

        case ProfileState.CONNECTED:
            status = send_follow_up_message(
                key=key,
                profile=profile,
                template_file=FOLLOWUP_TEMPLATE_FILE,
                template_type=FOLLOWUP_TEMPLATE_TYPE,
            )
            new_state = ProfileState.COMPLETED if status == MessageStatus.SENT else ProfileState.CONNECTED
        case _:
            raise TerminalStateError(f"Profile {public_identifier} is {old_state.value}")

    set_profile_state(session, profile, new_state)
    return profile
