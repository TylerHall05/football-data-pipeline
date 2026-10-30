import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pandas as pd
import psycopg
import pytest

from football_pipeline.config import get_database_url
from football_pipeline.db import apply_schema, connect
from football_pipeline.extract import parse_raw_csv
from football_pipeline.load import (
    load_leagues,
    stage_matches,
    upsert_matches_from_staging,
    upsert_teams_from_staging,
)
from football_pipeline.transform import deduplicate, transform_matches
from football_pipeline.validate import validate_matches

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_csv_bytes() -> bytes:
    """Synthetic E0 2024/25 sample with deliberate data-quality problems."""
    return (FIXTURES / "sample_E0_2425.csv").read_bytes()


@pytest.fixture
def clean_matches(sample_csv_bytes: bytes) -> pd.DataFrame:
    """The sample file after transform, validation and de-duplication (valid rows only)."""
    cleaned = transform_matches(parse_raw_csv(sample_csv_bytes, "2425", "E0"))
    valid, _ = validate_matches(cleaned)
    deduped, _ = deduplicate(valid)
    return deduped


@pytest.fixture(scope="session")
def db_url() -> str:
    """URL of a reachable Postgres. Skips locally if none; fails in CI (REQUIRE_DB=1)."""
    url = get_database_url()
    try:
        psycopg.connect(url, connect_timeout=3).close()
    except psycopg.OperationalError as exc:
        if os.environ.get("REQUIRE_DB"):
            raise
        pytest.skip(f"PostgreSQL not available: {exc}")
    return url


@pytest.fixture
def conn(db_url: str) -> Iterator[psycopg.Connection]:
    """A connection inside a fresh, throwaway schema with all migrations applied."""
    schema = f"test_{uuid.uuid4().hex[:10]}"
    with psycopg.connect(db_url, autocommit=True) as admin:
        admin.execute(f'CREATE SCHEMA "{schema}"')
    try:
        with connect(db_url, search_path=schema) as connection:
            apply_schema(connection)
            connection.commit()  # so tests can exercise rollback without losing the schema
            yield connection
    finally:
        with psycopg.connect(db_url, autocommit=True) as admin:
            admin.execute(f'DROP SCHEMA "{schema}" CASCADE')


@pytest.fixture
def loaded(conn, clean_matches):
    """A database connection already holding the cleaned sample matches."""
    load_leagues(conn)
    stage_matches(conn, clean_matches)
    upsert_teams_from_staging(conn)
    upsert_matches_from_staging(conn)
    return conn
