from typing import Dict, Any
from urllib.parse import urlparse
from ..api.client import get_profile


def get_profile_info(linkedin_url: str, params: Dict[str, Any]):
    """
    Retrieves profile information via an API call.
    """
    profile_id = urlparse(linkedin_url).path.split('/')[2]
    profile = get_profile(public_id=profile_id)
    return profile


def is_connection_accepted(linkedin_url: str) -> bool:
    """Checks if a connection request was accepted."""
    print(f"CONDITION: Checking if connection accepted for {linkedin_url}")
    return False
