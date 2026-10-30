"""Audit trail: one ingestion_runs row per league/season load, plus quarantined rows."""

from __future__ import annotations

import json

import pandas as pd
import psycopg
from psycopg.types.json import Jsonb


def start_run(conn: psycopg.Connection, league_code: str, season: str) -> int:
    """Open a run in 'running' state and return its id."""
    row = conn.execute(
        "INSERT INTO ingestion_runs (league_code, season) VALUES (%s, %s) RETURNING run_id",
        (league_code, season),
    ).fetchone()
    return row[0]


def finish_run(
    conn: psycopg.Connection,
    run_id: int,
    status: str,
    *,
    rows_extracted: int | None = None,
    rows_rejected: int | None = None,
    rows_duplicate: int | None = None,
    rows_loaded: int | None = None,
    error_message: str | None = None,
) -> None:
    """Close a run with its final status and row counts."""
    conn.execute(
        """UPDATE ingestion_runs
           SET finished_at = now(), status = %s, rows_extracted = %s, rows_rejected = %s,
               rows_duplicate = %s, rows_loaded = %s, error_message = %s
           WHERE run_id = %s""",
        (status, rows_extracted, rows_rejected, rows_duplicate, rows_loaded, error_message, run_id),
    )


def record_rejects(conn: psycopg.Connection, run_id: int, rejected: pd.DataFrame) -> int:
    """Store rejected rows as JSON with the reason(s) they failed. Returns the row count."""
    if rejected.empty:
        return 0
    reasons = rejected["reject_reason"].tolist()
    payloads = json.loads(
        rejected.drop(columns=["reject_reason"]).to_json(orient="records", date_format="iso")
    )
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO rejected_rows (run_id, reject_reason, row_data) VALUES (%s, %s, %s)",
            [(run_id, reason, Jsonb(data)) for reason, data in zip(reasons, payloads, strict=True)],
        )
    return len(payloads)
