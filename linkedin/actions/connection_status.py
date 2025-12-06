# linkedin/actions/connections.py
import logging  # ← added
from typing import Dict, Any

from linkedin.navigation.enums import ConnectionStatus
from linkedin.sessions import AccountSessionRegistry, AccountSession

logger = logging.getLogger(__name__)


def get_connection_status(
        account_session: AccountSession,
        profile: Dict[str, Any],
) -> ConnectionStatus:
    resources = account_session.resources
    logger.debug("Checking connection status for %s", profile.get("full_name", "unknown"))

    degree = profile.get("connection_degree")

    # ── Fast path: only trust degree=1 as definitively CONNECTED ──
    if degree == 1:
        logger.debug("Connection status from API (degree=1) → CONNECTED")
        return ConnectionStatus.CONNECTED

    # For degree=2, 3, or None → we CANNOT trust API alone
    # Because pending invitations still show degree 2/3
    logger.debug(
        "connection_degree=%s → cannot trust API (pending invites look same as not connected). "
        "Falling back to UI inspection.",
        degree
    )

    # ── UI-based detection (now the ONLY reliable source for PENDING) ──

    # 1. Pending invitation?
    if resources.page.locator('button[aria-label*="Pending"]:visible').count() > 0:
        logger.debug("Found visible 'Pending' button → PENDING")
        return ConnectionStatus.PENDING

    # 2. Already connected? (double-check even if degree != 1, edge cases exist)
    dist_locator = resources.page.locator('span[class*="distance-badge"]:visible')
    if dist_locator.count() > 0:
        badge_text = dist_locator.first.inner_text().strip()
        logger.debug("Distance badge: %r", badge_text)
        if badge_text.startswith("1"):
            logger.debug("Distance badge shows 1st → CONNECTED")
            return ConnectionStatus.CONNECTED

    # 3. Can send invitation?
    invite_btn = resources.page.locator('button[aria-label*="Invite"][aria-label*="to connect"]:visible')
    if invite_btn.count() > 0:
        logger.debug("Found 'Connect' / 'Invite' button → NOT_CONNECTED")
        return ConnectionStatus.NOT_CONNECTED

    # 4. Unknown
    logger.debug("No clear indicators → UNKNOWN")
    return ConnectionStatus.UNKNOWN


if __name__ == "__main__":
    import sys
    import logging
    from linkedin.sessions import SessionKey
    from linkedin.actions.search import search_profile

    from linkedin.campaigns.connect_follow_up import INPUT_CSV_PATH

    logging.basicConfig(
        level=logging.DEBUG,  # Changed to DEBUG for full logs
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if len(sys.argv) != 2:
        print("Usage: python -m linkedin.actions.connections <handle>")
        sys.exit(1)

    handle = sys.argv[1]
    key = SessionKey.make(
        handle=handle,
        campaign_name="test_status",
        csv_path=INPUT_CSV_PATH,
    )

    profile = {
        "full_name": "Bill Gates",
        "url": "https://www.linkedin.com/in/williamhgates/",
        "public_identifier": "williamhgates",
    }

    print(f"Checking connection status as @{handle} → {profile['full_name']}")
    print(f"Session key: {key}")

    # Navigate first
    account_session = AccountSessionRegistry.get_or_create_from_path(
        handle=key.handle,
        campaign_name=key.campaign_name,
        csv_path=INPUT_CSV_PATH,
    )
    search_profile(account_session, profile)

    # Then check status
    status = get_connection_status(account_session, profile)
    print(f"Connection status → {status.value}")
