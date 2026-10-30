"""Load stage: idempotent writes of clean data into PostgreSQL."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd
import psycopg

from football_pipeline.config import LEAGUES
from football_pipeline.transform import INT_COLUMNS, KEY_COLUMNS, OUTPUT_COLUMNS

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


@dataclass(frozen=True)
class LoadResult:
    """Outcome of an upsert. ``unchanged`` rows matched an existing identical row."""

    inserted: int
    updated: int
    unchanged: int

    @property
    def total(self) -> int:
        return self.inserted + self.updated + self.unchanged


def upsert_matches_from_staging(conn: psycopg.Connection) -> LoadResult:
    """Merge staged matches into ``matches`` using the fixture's natural key.

    Re-running with the same data is a no-op, and corrected source data updates the stored
    row. Rows are only rewritten when a value actually differs (IS DISTINCT FROM), so
    ``updated_at`` reflects real changes. ``xmax = 0`` distinguishes inserts from updates.
    """
    data_cols = [c for c in OUTPUT_COLUMNS if c not in KEY_COLUMNS]
    insert_cols = ", ".join(
        ["league_code", "season", "match_date", "home_team_id", "away_team_id", *data_cols]
    )
    select_cols = ", ".join(
        ["s.league_code", "s.season", "s.match_date", "h.team_id", "a.team_id"]
        + [f"s.{c}" for c in data_cols]
    )
    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in data_cols)
    old_vals = ", ".join(f"matches.{c}" for c in data_cols)
    new_vals = ", ".join(f"EXCLUDED.{c}" for c in data_cols)
    # data_cols are our own constants, never user input, so f-string SQL is safe here.
    sql = f"""
        INSERT INTO matches ({insert_cols})
        SELECT {select_cols}
        FROM {STAGING_TABLE} s
        JOIN teams h ON h.name = s.home_team
        JOIN teams a ON a.name = s.away_team
        ON CONFLICT ON CONSTRAINT uq_match_fixture DO UPDATE
        SET {set_clause}, updated_at = now()
        WHERE ({old_vals}) IS DISTINCT FROM ({new_vals})
        RETURNING (xmax = 0) AS inserted
    """
    flags = [row[0] for row in conn.execute(sql).fetchall()]
    staged = conn.execute(f"SELECT count(*) FROM {STAGING_TABLE}").fetchone()[0]
    inserted = sum(flags)
    updated = len(flags) - inserted
    return LoadResult(inserted, updated, staged - len(flags))
