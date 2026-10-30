from football_pipeline.db import apply_schema, migration_files


def test_migrations_are_found_in_order():
    names = [name for name, _ in migration_files()]
    assert names == sorted(names)
    assert names[0].startswith("001_")


def test_expected_tables_exist(conn):
    rows = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()"
    ).fetchall()
    assert {r[0] for r in rows} >= {
        "leagues",
        "teams",
        "matches",
        "ingestion_runs",
        "rejected_rows",
    }


def test_apply_schema_is_idempotent(conn):
    apply_schema(conn)  # second run on top of the fixture's first
    apply_schema(conn)
