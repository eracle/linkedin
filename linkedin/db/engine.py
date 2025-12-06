# linkedin/engine.py
import logging
from pathlib import Path
from typing import Optional, Dict, Any, TypeAlias, List

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, scoped_session, Session as SASession

from linkedin.api.logging import log_profiles
from linkedin.conf import get_account_config
from linkedin.db.models import Base, Profile as DbProfile, CampaignRun, _make_short_run_id
from linkedin.navigation.utils import url_to_public_id, public_id_to_url  # NEW imports

DatabaseSession: TypeAlias = SASession

logger = logging.getLogger(__name__)


class Database:
    """
    One account → one database.
    Profiles are saved instantly using public_identifier as PK.
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

        self.db_path = Path(db_path)

    def get_session(self):
        return self.Session()

    def close(self):
        """This is the ONLY place we sync to your backend."""
        logger.info("Database.close() triggered → syncing all unsynced profiles to cloud...")
        self._sync_all_unsynced_profiles()
        self.Session.remove()
        logger.info("Database closed and fully synced.")

    def _sync_all_unsynced_profiles(self):
        with self.get_session() as db_session:
            unsynced = db_session.query(DbProfile).filter_by(
                scraped=True,
                cloud_synced=False
            ).all()

            if not unsynced:
                logger.info("No scraped + unsynced profiles found.")
                return

            payload = [p.data for p in unsynced if p.data]
            if not payload:
                return

            success = log_profiles(payload)

            if success:
                for p in unsynced:
                    p.cloud_synced = True
                db_session.commit()
                logger.info(f"SUCCESS: Synced {len(payload)} profiles to cloud")
            else:
                logger.error("Sync failed — profiles remain unsynced. Will retry next close().")

    @classmethod
    def from_handle(cls, handle: str) -> "Database":
        logger.info(f"Creating Database instance for account handle: {handle}")
        config = get_account_config(handle)
        db_path = config["db_path"]
        logger.debug(f"Resolved db_path for {handle}: {db_path}")
        return cls(db_path)


# ─────────────────────────────────────────────────────────────────────────────
# CAMPAIGN FUNCTIONS — unchanged (still valid)
# ─────────────────────────────────────────────────────────────────────────────
def has_campaign_run(session: DatabaseSession, name: str, handle: str, input_hash: str) -> bool:
    return session.query(CampaignRun).filter_by(
        name=name, handle=handle, input_hash=input_hash
    ).first() is not None


def mark_campaign_run(
        session: DatabaseSession,
        name: str,
        handle: str,
        input_hash: str,
        short_id: str | None = None,
) -> str:
    if has_campaign_run(session, name, handle, input_hash):
        return session.query(CampaignRun.short_id).filter_by(
            name=name, handle=handle, input_hash=input_hash
        ).scalar()

    if short_id is None:
        short_id = _make_short_run_id(name, handle, input_hash)

    session.add(CampaignRun(
        name=name,
        handle=handle,
        input_hash=input_hash,
        short_id=short_id,
    ))
    session.commit()
    logger.info(f"Campaign run recorded → {name} | {handle} | {short_id}")
    return short_id


def get_campaign_short_id(session: DatabaseSession, name: str, handle: str, input_hash: str) -> str | None:
    return session.query(CampaignRun.short_id).filter_by(
        name=name, handle=handle, input_hash=input_hash
    ).scalar()


def update_campaign_stats(
        session: DatabaseSession,
        name: str,
        handle: str,
        input_hash: str,
        *,
        total_profiles: int | None = None,
        increment_enriched: int = 0,
        increment_connect_sent: int = 0,
        increment_accepted: int = 0,
        increment_followup_sent: int = 0,
        increment_completed: int = 0,
):
    run = session.query(CampaignRun).filter_by(
        name=name, handle=handle, input_hash=input_hash
    ).first()

    if not run:
        logger.warning(f"CampaignRun not found for stats update: {name}|{handle}")
        return

    if total_profiles is not None:
        run.total_profiles = total_profiles

    run.enriched += increment_enriched
    run.connect_sent += increment_connect_sent
    run.accepted += increment_accepted
    run.followup_sent += increment_followup_sent
    run.completed += increment_completed

    session.commit()
    logger.debug(f"Campaign stats updated → {run.short_id} | "
                 f"Enriched:{run.enriched} Connect:{run.connect_sent} "
                 f"Accepted:{run.accepted} Followup:{run.followup_sent} Done:{run.completed}")


def get_campaign_stats(session: DatabaseSession, name: str, handle: str, input_hash: str) -> dict | None:
    run = session.query(CampaignRun).filter_by(
        name=name, handle=handle, input_hash=input_hash
    ).first()
    if not run:
        return None
    return {
        "campaign_id": run.short_id,
        "total_profiles": run.total_profiles,
        "enriched": run.enriched,
        "connect_sent": run.connect_sent,
        "accepted": run.accepted,
        "followup_sent": run.followup_sent,
        "completed": run.completed,
        "last_updated": run.last_updated.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# NEW PROFILE LIFECYCLE — using public_identifier as PK
# ─────────────────────────────────────────────────────────────────────────────

def add_profile_urls(session: DatabaseSession, urls: List[str]):
    """Phase 1: Discover LinkedIn profiles → insert by public_identifier"""
    if not urls:
        return

    public_ids = {
        pid for url in urls
        if (pid := url_to_public_id(url))
    }

    if not public_ids:
        return

    to_insert = [{"public_identifier": pid} for pid in public_ids]
    session.execute(
        DbProfile.__table__.insert()
        .prefix_with("OR IGNORE")  # SQLite: do nothing on conflict
        .values(to_insert)
    )
    session.commit()

    logger.info(f"Discovered {len(public_ids)} unique LinkedIn profiles (public_identifier)")
    for pid in public_ids:
        logger.debug("Profile discovered → %s", public_id_to_url(pid))


def save_scraped_profile(
        session: DatabaseSession,
        url: str,
        profile_data: Dict[str, Any],
        raw_json: Dict[str, Any] | None = None,
):
    """Phase 2: Save scraped data using public_identifier"""
    public_id = url_to_public_id(url)

    profile = session.get(DbProfile, public_id)
    if profile is None:
        profile = DbProfile(public_identifier=public_id)

    profile.data = profile_data
    profile.raw_json = raw_json
    profile.scraped = True
    profile.cloud_synced = False
    profile.updated_at = func.now()

    session.merge(profile)
    session.commit()
    logger.info(f"Scraped profile saved → {public_id_to_url(public_id)}")


def get_next_url_to_scrape(session: DatabaseSession, limit: int = 1) -> List[str]:
    """Return clean LinkedIn URLs for unscraped profiles"""
    rows = session.query(DbProfile.public_identifier).filter_by(scraped=False).limit(limit).all()
    return [public_id_to_url(row.public_identifier) for row in rows]


def count_pending_scrape(session: DatabaseSession) -> int:
    return session.query(DbProfile).filter_by(scraped=False).count()


# Optional: Helper to get profile data by public_id (cleaner than old URL-based one)
def get_profile_by_public_id(session: DatabaseSession, public_id: str) -> Optional[Dict[str, Any]]:
    profile = session.get(DbProfile, public_id)
    return profile.data if profile and profile.scraped else None
