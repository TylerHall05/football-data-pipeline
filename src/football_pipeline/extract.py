"""Extract stage: locate and fetch raw season CSVs from football-data.co.uk."""

from __future__ import annotations

import re
from pathlib import Path

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
