"""Central configuration: leagues, season codes and database settings."""

from __future__ import annotations

import os
from datetime import date

DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/football"

# football-data.co.uk league code -> (name, country)
LEAGUES: dict[str, tuple[str, str]] = {
    "E0": ("Premier League", "England"),
    "E1": ("Championship", "England"),
    "E2": ("League One", "England"),
    "E3": ("League Two", "England"),
    "SC0": ("Scottish Premiership", "Scotland"),
    "D1": ("Bundesliga", "Germany"),
    "SP1": ("La Liga", "Spain"),
    "I1": ("Serie A", "Italy"),
    "F1": ("Ligue 1", "France"),
}


def get_database_url() -> str:
    """Return the database URL from DATABASE_URL, falling back to a local default."""
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def season_code(start_year: int) -> str:
    """Convert a season start year to football-data's code, e.g. 2025 -> '2526'."""
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def current_season_code(today: date | None = None) -> str:
    """Season code for the season in progress (seasons start around July/August)."""
    today = today or date.today()
    start_year = today.year if today.month >= 7 else today.year - 1
    return season_code(start_year)


def recent_seasons(n: int = 3, today: date | None = None) -> list[str]:
    """The last ``n`` season codes, oldest first, ending with the current season."""
    today = today or date.today()
    start_year = today.year if today.month >= 7 else today.year - 1
    return [season_code(start_year - i) for i in range(n - 1, -1, -1)]
