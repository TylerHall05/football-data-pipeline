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

INT_COLUMNS = [
    "home_goals",
    "away_goals",
    "ht_home_goals",
    "ht_away_goals",
    "home_shots",
    "away_shots",
    "home_shots_on_target",
    "away_shots_on_target",
    "home_fouls",
    "away_fouls",
    "home_corners",
    "away_corners",
    "home_yellows",
    "away_yellows",
    "home_reds",
    "away_reds",
]

# Variant spellings seen across sources -> the name used in football-data.co.uk.
# Extend this as new variants appear.
TEAM_ALIASES: dict[str, str] = {
    "Man Utd": "Man United",
    "Manchester United": "Man United",
    "Manchester City": "Man City",
    "Spurs": "Tottenham",
    "Nottingham Forest": "Nott'm Forest",
    "Nottm Forest": "Nott'm Forest",
    "Wolverhampton": "Wolves",
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


def clean_team_names(series: pd.Series) -> pd.Series:
    """Trim, collapse internal whitespace and apply known aliases to team names."""
    cleaned = series.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    cleaned = cleaned.mask(cleaned == "")
    return cleaned.replace(TEAM_ALIASES)


def clean_result(series: pd.Series) -> pd.Series:
    """Upper-case and trim H/D/A result codes; empty strings become missing."""
    cleaned = series.astype("string").str.strip().str.upper()
    return cleaned.mask(cleaned == "")


def to_nullable_int(series: pd.Series) -> pd.Series:
    """Convert to pandas nullable Int64; non-numeric and non-integral values become <NA>."""
    numeric = pd.to_numeric(series, errors="coerce")
    numeric = numeric.where(numeric == numeric.round())
    return numeric.astype("Int64")


def clean_text(series: pd.Series) -> pd.Series:
    """Trim free text (e.g. referee names); empty strings become missing."""
    cleaned = series.astype("string").str.strip()
    return cleaned.mask(cleaned == "")


def drop_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows with no data in any modelled column (trailing blank lines in the CSV)."""
    return df.dropna(how="all", subset=list(COLUMN_MAP.values())).reset_index(drop=True)


def transform_matches(raw: pd.DataFrame) -> pd.DataFrame:
    """Raw text frame -> typed, cleaned frame. Does not validate or deduplicate."""
    df = select_and_rename(raw)
    df["match_date"] = parse_dates(df["match_date"])
    df["kickoff_time"] = clean_kickoff_time(df["kickoff_time"])
    for col in ("home_team", "away_team"):
        df[col] = clean_team_names(df[col])
    for col in ("result", "ht_result"):
        df[col] = clean_result(df[col])
    df["referee"] = clean_text(df["referee"])
    for col in INT_COLUMNS:
        df[col] = to_nullable_int(df[col])
    return drop_empty_rows(df)


def deduplicate(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Drop repeated fixtures, keeping the last occurrence of each natural key.

    Returns the deduplicated frame and the number of rows removed. A fixture is identified by
    ``KEY_COLUMNS`` (league, season, date, home, away), which is also the table's unique key.
    """
    deduped = df.drop_duplicates(subset=KEY_COLUMNS, keep="last").reset_index(drop=True)
    return deduped, len(df) - len(deduped)
