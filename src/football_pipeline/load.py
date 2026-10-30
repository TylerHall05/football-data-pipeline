"""Load stage: idempotent writes of clean data into PostgreSQL."""

from __future__ import annotations

import logging

import pandas as pd
import psycopg

from football_pipeline.config import LEAGUES
from football_pipeline.transform import INT_COLUMNS, OUTPUT_COLUMNS

logger = logging.getLogger(__name__)


def load_leagues(conn: psycopg.Connection) -> int:
    """Upsert the league reference table from config. Returns the number of leagues."""
    rows = [(code, name, country) for code, (name, country) in LEAGUES.items()]
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO leagues (league_code, name, country) VALUES (%s, %s, %s)
               ON CONFLICT (league_code) DO UPDATE
               SET name = EXCLUDED.name, country = EXCLUDED.country""",
            rows,
        )
    return len(rows)


STAGING_TABLE = "stg_matches"
_DATE_COLUMNS = {"match_date": "date", "kickoff_time": "time"}


def staging_columns() -> dict[str, str]:
    """Column name -> SQL type for the staging table, derived from the transform output."""
    return {
        col: _DATE_COLUMNS.get(col, "smallint" if col in INT_COLUMNS else "text")
        for col in OUTPUT_COLUMNS
    }


def _to_python(value: object) -> object:
    """Convert pandas/numpy scalars (incl. NA/NaT) into plain values psycopg can write."""
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    return value.item() if hasattr(value, "item") else value


def stage_matches(conn: psycopg.Connection, df: pd.DataFrame) -> int:
    """Bulk-copy a cleaned frame into a temporary staging table. Returns the row count."""
    columns = staging_columns()
    ddl = ", ".join(f"{name} {sql_type}" for name, sql_type in columns.items())
    conn.execute(f"DROP TABLE IF EXISTS {STAGING_TABLE}")
    conn.execute(f"CREATE TEMP TABLE {STAGING_TABLE} ({ddl}) ON COMMIT DROP")
    with conn.cursor() as cur:
        with cur.copy(f"COPY {STAGING_TABLE} ({', '.join(columns)}) FROM STDIN") as copy:
            for row in df[list(columns)].itertuples(index=False, name=None):
                copy.write_row([_to_python(v) for v in row])
    return len(df)


def upsert_teams_from_staging(conn: psycopg.Connection) -> int:
    """Insert any team in staging that is not yet in ``teams``. Returns how many were new."""
    cur = conn.execute(
        f"""INSERT INTO teams (name)
            SELECT home_team FROM {STAGING_TABLE}
            UNION
            SELECT away_team FROM {STAGING_TABLE}
            ON CONFLICT (name) DO NOTHING"""
    )
    return cur.rowcount
