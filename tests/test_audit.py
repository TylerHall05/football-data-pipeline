import pytest

from football_pipeline.audit import finish_run, record_rejects, start_run
from football_pipeline.extract import parse_raw_csv
from football_pipeline.transform import transform_matches
from football_pipeline.validate import validate_matches


def test_run_lifecycle(conn):
    run_id = start_run(conn, "E0", "2425")
    status, finished = conn.execute(
        "SELECT status, finished_at FROM ingestion_runs WHERE run_id = %s", (run_id,)
    ).fetchone()
    assert (status, finished) == ("running", None)

    finish_run(conn, run_id, "succeeded", rows_extracted=15, rows_rejected=3, rows_loaded=11)
    row = conn.execute(
        "SELECT status, finished_at IS NOT NULL, rows_extracted, rows_rejected, rows_loaded "
        "FROM ingestion_runs WHERE run_id = %s",
        (run_id,),
    ).fetchone()
    assert row == ("succeeded", True, 15, 3, 11)


def test_failed_run_keeps_the_error(conn):
    run_id = start_run(conn, "E0", "2425")
    finish_run(conn, run_id, "failed", error_message="boom")
    assert conn.execute("SELECT error_message FROM ingestion_runs").fetchone()[0] == "boom"


def test_invalid_status_is_rejected(conn):
    run_id = start_run(conn, "E0", "2425")
    with pytest.raises(Exception, match="ingestion_runs_status_check"):
        finish_run(conn, run_id, "weird")


def test_rejected_rows_are_stored_with_reasons(conn, sample_csv_bytes):
    cleaned = transform_matches(parse_raw_csv(sample_csv_bytes, "2425", "E0"))
    _, rejected = validate_matches(cleaned)
    run_id = start_run(conn, "E0", "2425")
    assert record_rejects(conn, run_id, rejected) == len(rejected) == 3

    rows = conn.execute(
        "SELECT reject_reason, row_data FROM rejected_rows ORDER BY reject_id"
    ).fetchall()
    reasons = {reason for reason, _ in rows}
    assert "result_contradicts_score" in reasons
    contradicted = next(data for reason, data in rows if reason == "result_contradicts_score")
    assert contradicted["home_team"] == "Fulham"
    assert contradicted["match_date"].startswith("2024-08-31")


def test_no_rejects_writes_nothing(conn, clean_matches):
    run_id = start_run(conn, "E0", "2425")
    assert record_rejects(conn, run_id, clean_matches.assign(reject_reason="x").iloc[0:0]) == 0
