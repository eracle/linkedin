# linkedin/csv_utils.py
from pathlib import Path
from typing import List

import pandas as pd


def load_profile_urls_from_csv(csv_path: Path | str) -> List[str]:
    """
    Loads LinkedIn profile URLs from a CSV file.
    Assumes the file has at least one column containing URLs.
    Supported column names (case-insensitive):
        - url
        - linkedin_url
        - profile_url
        - Url, URL, etc.

    Returns a clean list of string URLs (deduped, stripped, no NaN).
    """
    csv_path = Path(csv_path)
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    # Find the first column that looks like it contains URLs
    possible_cols = ["url", "linkedin_url", "profile_url"]
    url_column = next(
        (col for col in df.columns if col.lower() in [c.lower() for c in possible_cols]),
        None,
    )

    if url_column is None:
        raise ValueError(
            f"Could not find a URL column in {csv_path}\n"
            f"   Found columns: {list(df.columns)}\n"
            f"   Expected one of: {possible_cols}"
        )

    urls = (
        df[url_column]
        .astype(str)
        .str.strip()
        .replace({"nan": None, "<NA>": None})
        .dropna()
        .tolist()
    )

    return urls
