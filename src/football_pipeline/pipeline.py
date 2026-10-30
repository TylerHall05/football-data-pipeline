"""Orchestration: extract -> transform -> validate -> load for one league/season."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import psycopg
import requests

from football_pipeline.audit import finish_run, record_rejects, start_run
from football_pipeline.db import apply_schema
from football_pipeline.extract import SeasonNotAvailable, extract_season
from football_pipeline.load import (
    LoadResult,
    load_leagues,
    stage_matches,
    upsert_matches_from_staging,
    upsert_teams_from_staging,
)
from football_pipeline.transform import deduplicate, transform_matches
from football_pipeline.validate import validate_matches

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunSummary:
    """What happened to one league/season. Counts satisfy:
    extracted = rejected + duplicates + load.total  (when status is 'succeeded').
    """

    league_code: str
    season: str
    status: str
    extracted: int = 0
    rejected: int = 0
    duplicates: int = 0
    load: LoadResult | None = None
    error: str | None = None


def run_season(
    conn: psycopg.Connection,
    league_code: str,
    season: str,
    raw_dir: Path | str,
    offline: bool = False,
    session: requests.Session | None = None,
) -> RunSummary:
    """Load one league/season. The data load is a single transaction: it fully applies or not at
    all, while the audit row is committed independently so failures stay visible.
    """
    run_id = start_run(conn, league_code, season)
    conn.commit()
    try:
        raw = extract_season(season, league_code, raw_dir, offline=offline, session=session)
        cleaned = transform_matches(raw)
        valid, rejected = validate_matches(cleaned)
        deduped, n_duplicates = deduplicate(valid)

        record_rejects(conn, run_id, rejected)
        stage_matches(conn, deduped)
        upsert_teams_from_staging(conn)
        result = upsert_matches_from_staging(conn)
        finish_run(
            conn,
            run_id,
            "succeeded",
            rows_extracted=len(cleaned),
            rows_rejected=len(rejected),
            rows_duplicate=n_duplicates,
            rows_loaded=result.total,
        )
        conn.commit()
        logger.info("%s %s: %s", league_code, season, result)
        return RunSummary(
            league_code, season, "succeeded", len(cleaned), len(rejected), n_duplicates, result
        )
    except SeasonNotAvailable:
        conn.rollback()
        finish_run(conn, run_id, "skipped", error_message="season file not available")
        conn.commit()
        logger.warning("%s %s: not available, skipped", league_code, season)
        return RunSummary(league_code, season, "skipped")
    except Exception as exc:
        conn.rollback()
        finish_run(conn, run_id, "failed", error_message=f"{type(exc).__name__}: {exc}")
        conn.commit()
        logger.exception("%s %s failed", league_code, season)
        raise


def run_all(
    conn: psycopg.Connection,
    league_codes: list[str],
    seasons: list[str],
    raw_dir: Path | str,
    offline: bool = False,
    session: requests.Session | None = None,
) -> list[RunSummary]:
    """Ensure the schema and leagues exist, then load every league/season combination.

    One failing league/season does not stop the others; failures come back in the summaries.
    """
    apply_schema(conn)
    load_leagues(conn)
    conn.commit()

    summaries = []
    for season in seasons:
        for league_code in league_codes:
            try:
                summaries.append(run_season(conn, league_code, season, raw_dir, offline, session))
            except Exception as exc:  # already logged and audited in run_season
                summaries.append(
                    RunSummary(league_code, season, "failed", error=f"{type(exc).__name__}: {exc}")
                )
    return summaries
