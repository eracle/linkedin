# linkedin/db_models.py

import hashlib

from sqlalchemy import Column, String, JSON, DateTime, Boolean, Integer
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


def _make_short_run_id(name: str, handle: str, input_hash: str) -> str:
    """12-char deterministic ID – perfect for logs + Temporal workflow IDs"""
    return hashlib.sha256(f"{name}|{handle}|{input_hash}".encode()).hexdigest()[:12]


class CampaignRun(Base):
    __tablename__ = "campaign_runs"

    name = Column(String, primary_key=True)
    handle = Column(String, primary_key=True)
    input_hash = Column(String(64), primary_key=True)

    run_at = Column(DateTime, server_default=func.now(), nullable=False)
    short_id = Column(String(12), nullable=False, unique=True, index=True)

    total_profiles = Column(Integer, default=0, nullable=False)
    enriched = Column(Integer, default=0, nullable=False)
    connect_sent = Column(Integer, default=0, nullable=False)
    accepted = Column(Integer, default=0, nullable=False)
    followup_sent = Column(Integer, default=0, nullable=False)
    completed = Column(Integer, default=0, nullable=False)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __init__(self, name: str, handle: str, input_hash: str, short_id: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.handle = handle
        self.input_hash = input_hash
        self.short_id = short_id or _make_short_run_id(name, handle, input_hash)


class Profile(Base):
    __tablename__ = 'profiles'

    # USING public_identifier as primary key
    public_identifier = Column(String, primary_key=True)

    # Parsed / cleaned data (what you return from get_profile)
    profile = Column(JSON, nullable=True)

    # Full raw JSON from LinkedIn's API (for debugging, re-parsing, etc.)
    data = Column(JSON, nullable=True)

    # Whether this profile has been sent to your backend / cloud / CRM
    cloud_synced = Column(Boolean, default=False, server_default='false', nullable=False)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    state = Column(String, nullable=False, default="discovered")
