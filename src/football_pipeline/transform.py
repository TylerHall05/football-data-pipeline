"""Transform stage: turn raw text columns into clean, typed, validated match records."""

from __future__ import annotations

import pandas as pd

# football-data.co.uk column -> warehouse column
COLUMN_MAP: dict[str, str] = {
    "Date": "match_date",
    "Time": "kickoff_time",
    "HomeTeam": "home_team",
    "AwayTeam": "away_team",
    "FTHG": "home_goals",
    "FTAG": "away_goals",
    "FTR": "result",
    "HTHG": "ht_home_goals",
    "HTAG": "ht_away_goals",
    "HTR": "ht_result",
    "Referee": "referee",
    "HS": "home_shots",
    "AS": "away_shots",
    "HST": "home_shots_on_target",
    "AST": "away_shots_on_target",
    "HF": "home_fouls",
    "AF": "away_fouls",
    "HC": "home_corners",
    "AC": "away_corners",
    "HY": "home_yellows",
    "AY": "away_yellows",
    "HR": "home_reds",
    "AR": "away_reds",
}

KEY_COLUMNS = ["league_code", "season", "match_date", "home_team", "away_team"]
OUTPUT_COLUMNS = ["league_code", "season", *COLUMN_MAP.values()]


def select_and_rename(raw: pd.DataFrame) -> pd.DataFrame:
    """Keep only the columns we model, renamed to snake_case.

    Columns absent from older seasons (kick-off time, referee, shots...) become empty
    rather than raising, so every season produces the same shape.
    """
    wanted = ["league_code", "season", *COLUMN_MAP]
    return raw.reindex(columns=wanted).rename(columns=COLUMN_MAP)[OUTPUT_COLUMNS]


def parse_dates(series: pd.Series) -> pd.Series:
    """Parse day-first dates in either dd/mm/yyyy or dd/mm/yy form; bad values become NaT."""
    cleaned = series.astype("string").str.strip()
    return pd.to_datetime(cleaned, format="mixed", dayfirst=True, errors="coerce")


def clean_kickoff_time(series: pd.Series) -> pd.Series:
    """Normalise kick-off times to zero-padded 'HH:MM'; anything else becomes missing."""
    cleaned = series.astype("string").str.strip()
    valid = cleaned.str.fullmatch(r"([01]?\d|2[0-3]):[0-5]\d").fillna(False).astype(bool)
    return cleaned.where(valid).str.zfill(5)
