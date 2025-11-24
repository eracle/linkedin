# linkedin/database.py
import logging
from typing import Optional, Dict, Any

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, scoped_session

from linkedin.api.logging import log_profiles
from linkedin.conf import get_account_config
from linkedin.db_models import Base, Profile as DbProfile

logger = logging.getLogger(__name__)


class Database:
    """
    One account → one database.
    Profiles are saved instantly.
    Sync to cloud happens ONLY when close() is called.
    """

    def __init__(self, db_path: str):
        db_url = f"sqlite:///{db_path}"
        logger.info(f"Initializing database at {db_path}")
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        logger.debug("Database tables ensured (create_all ran)")

        session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(session_factory)

    def get_session(self):
        return self.Session()

    def close(self):
        """This is the ONLY place we sync to your backend."""
        logger.info("Database.close() triggered → syncing all unsynced profiles to cloud...")
        self._sync_all_unsynced_profiles()
        self.Session.remove()
        logger.info("Database closed and fully synced.")

    def _sync_all_unsynced_profiles(self):
        with self.get_session() as session:
            unsynced = session.query(DbProfile).filter_by(cloud_synced=False).all()
            if not unsynced:
                logger.info("No unsynced profiles found.")
                return

            payload = [p.data for p in unsynced if p.data]

            success = log_profiles(payload)

            if success:
                for p in unsynced:
                    p.cloud_synced = True
                session.commit()
                logger.info(f"SUCCESS: Synced {len(payload)} profiles to cloud")
            else:
                logger.error("Sync failed — profiles remain unsynced. Will retry next close().")

    @classmethod
    def from_handle(cls, handle: str) -> "Database":
        """
        Convenience factory: creates a fully configured Database instance for a given account handle.
        """
        logger.info(f"Creating Database instance for account handle: {handle}")
        config = get_account_config(handle)
        db_path = config["db_path"]
        logger.debug(f"Resolved db_path for {handle}: {db_path}")
        return cls(db_path)


def save_profile(session, profile_data: Dict[str, Any], raw_json: Dict[str, Any], linkedin_url: str):
    """
    Saves or updates a profile (both parsed data and raw JSON).
    Sets cloud_synced=False on insert.
    """
    existing = session.query(DbProfile).filter_by(linkedin_url=linkedin_url).first()

    if existing:
        logger.debug(f"Updating existing profile: {linkedin_url}")
        existing.data = profile_data
        existing.raw_json = raw_json
        existing.updated_at = func.now()
    else:
        logger.info(f"Saving new profile: {linkedin_url}")
        session.add(DbProfile(
            linkedin_url=linkedin_url,
            data=profile_data,
            raw_json=raw_json,
            cloud_synced=False,
        ))

    session.commit()


def get_profile(session, linkedin_url: str) -> Optional[Dict[str, Any]]:
    """
    Returns parsed profile data if exists in DB, else None.
    """
    result = session.query(DbProfile).filter_by(linkedin_url=linkedin_url).first()
    return result.data if result else None
