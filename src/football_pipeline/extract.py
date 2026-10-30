"""Extract stage: locate and fetch raw season CSVs from football-data.co.uk."""

from __future__ import annotations

import io
import logging
import re
import time
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://www.football-data.co.uk/mmz4281"
_SEASON_RE = re.compile(r"^(\d{2})(\d{2})$")


def validate_season(season: str) -> str:
    """Check a season code is well formed, e.g. '2526' (2025/26)."""
    match = _SEASON_RE.match(season)
    if not match or (int(match.group(1)) + 1) % 100 != int(match.group(2)):
        raise ValueError(f"Invalid season code {season!r}; expected e.g. '2526'")
    return season


def season_url(season: str, league: str) -> str:
    """URL of the CSV for one league and season."""
    return f"{BASE_URL}/{validate_season(season)}/{league}.csv"


def raw_path(raw_dir: Path | str, season: str, league: str) -> Path:
    """Where the raw CSV for a league/season is cached on disk."""
    return Path(raw_dir) / f"{league}_{validate_season(season)}.csv"


class SeasonNotAvailable(Exception):
    """The requested league/season file does not exist (yet)."""


def download_csv(
    url: str,
    session: requests.Session | None = None,
    retries: int = 3,
    backoff: float = 1.0,
    timeout: float = 30.0,
) -> bytes:
    """Download ``url`` and return the body, retrying transient failures.

    Raises ``SeasonNotAvailable`` on HTTP 404 (e.g. a season not yet published).
    Network errors and 5xx responses are retried with exponential backoff.
    """
    session = session or requests.Session()
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=timeout)
        except requests.RequestException as exc:
            last_error = exc
        else:
            if response.status_code == 404:
                raise SeasonNotAvailable(url)
            if response.status_code < 500:
                response.raise_for_status()
                return response.content
            last_error = requests.HTTPError(f"{response.status_code} for {url}")
        if attempt < retries:
            delay = backoff * 2 ** (attempt - 1)
            logger.warning(
                "Attempt %d/%d failed for %s (%s); retrying in %.1fs",
                attempt,
                retries,
                url,
                last_error,
                delay,
            )
            time.sleep(delay)
    raise RuntimeError(f"Failed to download {url} after {retries} attempts") from last_error


def decode_bytes(content: bytes) -> str:
    """Decode a CSV body; football-data files are UTF-8 (with BOM) or Windows-1252/Latin-1."""
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("latin-1")


def parse_raw_csv(content: bytes, season: str, league: str) -> pd.DataFrame:
    """Parse raw CSV bytes into an all-string DataFrame, tagged with season and league.

    Everything is read as text so that typing and validation happen explicitly in the
    transform stage. Fully blank rows and stray unnamed columns are dropped.
    """
    frame = pd.read_csv(io.StringIO(decode_bytes(content)), dtype=str, on_bad_lines="skip")
    frame.columns = [str(c).strip() for c in frame.columns]
    frame = frame.loc[:, ~frame.columns.str.startswith("Unnamed")]
    frame = frame.dropna(how="all").reset_index(drop=True)
    frame.insert(0, "league_code", league)
    frame.insert(1, "season", validate_season(season))
    return frame


def extract_season(
    season: str,
    league: str,
    raw_dir: Path | str,
    offline: bool = False,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    """Return the raw DataFrame for one league/season.

    Online mode downloads the CSV and caches the untouched bytes under ``raw_dir`` so a
    run can be replayed or audited later. Offline mode reads only from that cache.
    Raises ``SeasonNotAvailable`` if the file does not exist remotely or in the cache.
    """
    path = raw_path(raw_dir, season, league)
    if offline:
        if not path.exists():
            raise SeasonNotAvailable(str(path))
        content = path.read_bytes()
    else:
        content = download_csv(season_url(season, league), session=session)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        logger.info("Cached %s (%d bytes)", path, len(content))
    return parse_raw_csv(content, season, league)
