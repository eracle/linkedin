# linkedin/actions/connections.py
from typing import Dict, Any

from linkedin.navigation.enums import ConnectionStatus
from linkedin.sessions import AccountSessionRegistry, SessionKey


def get_connection_status(
        key: SessionKey,
        profile: Dict[str, Any],
) -> ConnectionStatus:
    """
    Checks the current connection status of a profile using the correct persistent session.

    Usage:
        from linkedin.actions.connections import get_connection_status
        from linkedin.sessions import SessionKey

        status = get_connection_status(
            key=SessionKey.make("john_doe", "outreach", "leads.csv"),
            profile=profile_dict
        )
    """
    # Resolve session from key — clean, safe, and always correct
    session = AccountSessionRegistry.get_or_create(
        handle=key.handle,
        campaign_name=key.campaign_name,
        csv_hash=key.csv_hash,
    )

    resources = session.resources

    # 1. Pending
    if resources.page.locator('button[aria-label*="Pending"]:visible').count() > 0:
        return ConnectionStatus.PENDING

    # 2. Already connected – distance badge starts with "1"
    dist_locator = resources.page.locator('span[class^="distance-badge"]:visible')
    if dist_locator.count() > 0:
        badge_text = dist_locator.first.inner_text().strip()
        if badge_text.startswith("1"):
            return ConnectionStatus.CONNECTED

    # 3. Can send a request
    if resources.page.locator('button[aria-label*="Invite"]:visible').count() > 0:
        return ConnectionStatus.NOT_CONNECTED

    # 4. Fallback
    return ConnectionStatus.UNKNOWN


if __name__ == "__main__":
    import sys
    import logging
    from pathlib import Path
    from linkedin.sessions import SessionKey
    from linkedin.activities.search import search_profile

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if len(sys.argv) != 2:
        print("Usage: python -m linkedin.actions.connections <handle>")
        sys.exit(1)

    handle = sys.argv[1]
    key = SessionKey.make(
        handle=handle,
        campaign_name="test_status",
        csv_path=Path("dummy.csv"),  # hash will be computed automatically
    )

    profile = {
        "full_name": "Bill Gates",
        "linkedin_url": "https://www.linkedin.com/in/williamhgates/",
        "public_id": "williamhgates",
    }

    print(f"Checking connection status as @{handle} → {profile['full_name']}")
    print(f"Session key: {key}")

    # Navigate first
    session = AccountSessionRegistry.get_or_create_from_path(
        handle=key.handle,
        campaign_name=key.campaign_name,
        csv_path=Path("dummy.csv"),
    )
    search_profile(session, profile)

    # Then check status
    status = get_connection_status(key, profile)
    print(f"Connection status → {status.value}")
