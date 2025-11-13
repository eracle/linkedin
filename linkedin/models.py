# linkedin/models.py
from pydantic import BaseModel
from typing import List, Dict, Any

class Profile(BaseModel):
    """
    Pydantic model for a LinkedIn Profile.
    This model represents the structured data scraped for a LinkedIn user.
    """
    linkedin_url: str
    public_id: str
    profile_id: int
    first_name: str
    last_name: str
    headline: str
    summary: str
    country: str
    city: str
    experience: List[Dict[str, Any]]
    education: List[Dict[str, Any]]
    skills: List[str]
    # ... and other fields from the API


class Company(BaseModel):
    """
    Pydantic model for a LinkedIn Company.
    This model represents the structured data scraped for a LinkedIn company page.
    """
    linkedin_url: str
    name: str
    tagline: str
    about: str
    website: str
    industry: str
    company_size: str
    headquarters: Dict[str, str]
    # ... and other fields from the API
