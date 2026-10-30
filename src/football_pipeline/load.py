"""Load stage: idempotent writes of clean data into PostgreSQL."""

from __future__ import annotations

import logging

import psycopg

from football_pipeline.config import LEAGUES

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
