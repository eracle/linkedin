# linkedin/campaigns/start.py
import csv
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def _normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url.endswith("/"):
        url += "/"
    return url.lower()


def _compute_csv_hash(input_csv: Path) -> str:
    """Deterministic 12-char hash from sorted, normalized URLs"""
    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    urls = []
    with open(input_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "url" not in reader.fieldnames:
            raise ValueError("CSV must have 'url' column")
        for row in reader:
            raw = row["url"]
            if raw:
                urls.append(_normalize_url(raw))

    urls = sorted(set(urls))  # dedupe + sort = deterministic
    content = "\n".join(urls).encode("utf-8")
    return hashlib.sha256(content).hexdigest()[:12]


def init_campaign(context: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    NEW INIT STEP – called once per campaign run
    - Computes hash
    - Sets context["csv_hash"]
    - Returns list of raw profiles (just linkedin_url)
    - Never re-executes if DB exists (handled by workflow)
    """
    params = context["params"]
    input_csv_path = Path(params["input_csv"]).expanduser().resolve()

    csv_hash = _compute_csv_hash(input_csv_path)
    context["csv_hash"] = csv_hash
    context["input_csv"] = str(input_csv_path)

    logger.info(f"Campaign init → CSV hash: {csv_hash} ({input_csv_path.name})")

    raw_profiles: List[Dict[str, str]] = []
    with open(input_csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_url = row["url"]
            if raw_url:
                normalized = _normalize_url(raw_url)
                raw_profiles.append({"linkedin_url": normalized})

    logger.info(f"Init complete → {len(raw_profiles)} unique profiles loaded")
    return raw_profiles