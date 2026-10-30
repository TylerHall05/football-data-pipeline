"""Database access: connections and schema migrations."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import resources

import psycopg

from football_pipeline.config import get_database_url

logger = logging.getLogger(__name__)


@contextmanager
def connect(url: str | None = None, search_path: str | None = None) -> Iterator[psycopg.Connection]:
    """Open a connection that commits on success and rolls back on error.

    ``search_path`` lets tests run inside a throwaway schema.
    """
    options = f"-c search_path={search_path}" if search_path else None
    with psycopg.connect(url or get_database_url(), options=options) as conn:
        yield conn


def migration_files() -> list[tuple[str, str]]:
    """Packaged ``sql/NNN_*.sql`` files as (name, sql), in filename order."""
    root = resources.files("football_pipeline") / "sql"
    files = sorted((p for p in root.iterdir() if p.name.endswith(".sql")), key=lambda p: p.name)
    return [(p.name, p.read_text(encoding="utf-8")) for p in files]


def apply_schema(conn: psycopg.Connection) -> list[str]:
    """Run every migration in order. Safe to repeat because the DDL is idempotent."""
    applied = []
    for name, sql in migration_files():
        conn.execute(sql)
        applied.append(name)
        logger.info("Applied %s", name)
    return applied
