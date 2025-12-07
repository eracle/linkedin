# linkedin/db/engine.py
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, unquote

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, scoped_session

from linkedin.api.logging import log_profiles
from linkedin.conf import get_account_config
from linkedin.db.models import Base, Profile as DbProfile, CampaignRun, _make_short_run_id
from linkedin.sessions.account import AccountSession

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
# CAMPAIGN FUNCTIONS — ONLY AccountSession
# ─────────────────────────────────────────────────────────────────────────────
def has_campaign_run(session: AccountSession, name: str, input_hash: str) -> bool:
    return session.db.get_session().query(CampaignRun).filter_by(
        name=name, handle=session.handle, input_hash=input_hash
    ).first() is not None


def mark_campaign_run(
        session: AccountSession,
        name: str,
        input_hash: str,
        short_id: Optional[str] = None,
) -> str:
    db = session.db.get_session()

    if has_campaign_run(session, name, input_hash):
        return db.query(CampaignRun.short_id).filter_by(
            name=name, handle=session.handle, input_hash=input_hash
        ).scalar()

    short_id = short_id or _make_short_run_id(name, session.handle, input_hash)
    db.add(CampaignRun(
        name=name,
        handle=session.handle,
        input_hash=input_hash,
        short_id=short_id,
    ))
    db.commit()
    logger.info(f"Campaign run recorded → {name} | {session.handle} | {short_id}")
    return short_id


def get_campaign_short_id(session: AccountSession, name: str, input_hash: str) -> Optional[str]:
    return session.db.get_session().query(CampaignRun.short_id).filter_by(
        name=name, handle=session.handle, input_hash=input_hash
    ).scalar()


def update_campaign_stats(
        session: AccountSession,
        name: str,
        input_hash: str,
        *,
        total_profiles: Optional[int] = None,
        increment_enriched: int = 0,
        increment_connect_sent: int = 0,
        increment_accepted: int = 0,
        increment_followup_sent: int = 0,
        increment_completed: int = 0,
):
    db = session.db.get_session()
    run = db.query(CampaignRun).filter_by(
        name=name, handle=session.handle, input_hash=input_hash
    ).first()

    if not run:
        logger.warning(f"CampaignRun not found: {name} | {session.handle}")
        return

    if total_profiles is not None:
        run.total_profiles = total_profiles
    run.enriched += increment_enriched
    run.connect_sent += increment_connect_sent
    run.accepted += increment_accepted
    run.followup_sent += increment_followup_sent
    run.completed += increment_completed
    db.commit()

    logger.debug(f"Campaign stats updated → {run.short_id} | "
                 f"Enriched:{run.enriched} Connect:{run.connect_sent} "
                 f"Accepted:{run.accepted} Followup:{run.followup_sent} Done:{run.completed}")


def get_campaign_stats(session: AccountSession, name: str, input_hash: str) -> Optional[dict]:
    run = session.db.get_session().query(CampaignRun).filter_by(
        name=name, handle=session.handle, input_hash=input_hash
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
# PROFILE LIFECYCLE
# ─────────────────────────────────────────────────────────────────────────────
def add_profile_urls(session: AccountSession, urls: List[str]):
    if not urls:
        return

    public_ids = {pid for url in urls if (pid := url_to_public_id(url))}
    if not public_ids:
        return

    db = session.db.get_session()
    to_insert = [{"public_identifier": pid} for pid in public_ids]
    db.execute(
        DbProfile.__table__.insert()
        .prefix_with("OR IGNORE")
        .values(to_insert)
    )
    db.commit()

    logger.info(f"Discovered {len(public_ids)} unique LinkedIn profiles")
    for pid in public_ids:
        logger.debug("Profile discovered → %s", public_id_to_url(pid))


def save_scraped_profile(
        session: AccountSession,
        url: str,
        profile_data: Dict[str, Any],
        raw_json: Optional[Dict[str, Any]] = None,
):
    public_id = url_to_public_id(url)
    db = session.db.get_session()

    profile = db.get(DbProfile, public_id) or DbProfile(public_identifier=public_id)
    profile.data = profile_data
    profile.raw_json = raw_json
    profile.scraped = True
    profile.cloud_synced = False
    profile.updated_at = func.now()

    db.merge(profile)
    db.commit()
    logger.info(f"Scraped profile saved → {public_id_to_url(public_id)}")


def get_next_url_to_scrape(session: AccountSession, limit: int = 1) -> List[str]:
    rows = session.db.get_session() \
        .query(DbProfile.public_identifier) \
        .filter_by(scraped=False) \
        .limit(limit).all()
    return [public_id_to_url(row.public_identifier) for row in rows]


def count_pending_scrape(session: AccountSession) -> int:
    return session.db.get_session().query(DbProfile).filter_by(scraped=False).count()


def get_profile_by_public_id(session: AccountSession, public_id: str) -> Optional[Dict[str, Any]]:
    profile = session.db.get_session().get(DbProfile, public_id)
    return profile.data if profile and profile.scraped else None


def url_to_public_id(url: str) -> str:
    """
    Convert any LinkedIn profile URL → public_identifier (e.g. 'john-doe-1a2b3c4d')

    Examples:
      "https://www.linkedin.com/in/john-doe-1a2b3c4d/?originalSubdomain=fr" → "john-doe-1a2b3c4d"
      "https://linkedin.com/in/alice/" → "alice"
      "http://linkedin.com/in/bob-123/" → "bob-123"
    """
    if not url:
        return ""

    parsed = urlparse(url.strip().lower())
    if not parsed.path:
        return ""

    # Remove leading '/in/' and trailing slash
    path = parsed.path.strip("/")
    if not path.startswith("in/"):
        return ""

    public_id = path[3:]  # strip the "in/"
    if public_id.endswith("/"):
        public_id = public_id[:-1]

    return unquote(public_id)


def public_id_to_url(public_id: str) -> str:
    """
    Convert public_identifier back to a clean LinkedIn profile URL.

    You can choose www or not — both work, www is slightly more common.
    """
    if not public_id:
        return ""

    public_id = public_id.strip("/")
    scheme = "https"
    domain = "linkedin.com"
    return f"{scheme}://{domain}/in/{public_id}/"
