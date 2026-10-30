import pytest

from football_pipeline import pipeline
from football_pipeline.extract import raw_path
from football_pipeline.load import LoadResult, load_leagues
from football_pipeline.pipeline import run_season


@pytest.fixture
def raw_dir(tmp_path, sample_csv_bytes):
    """A cache directory holding the sample file, so runs are offline and deterministic."""
    path = raw_path(tmp_path, "2425", "E0")
    path.write_bytes(sample_csv_bytes)
    return tmp_path


@pytest.fixture
def ready(conn):
    load_leagues(conn)
    conn.commit()
    return conn


def test_successful_run_reports_every_row(ready, raw_dir):
    summary = run_season(ready, "E0", "2425", raw_dir, offline=True)
    assert summary.status == "succeeded"
    assert (summary.extracted, summary.rejected, summary.duplicates) == (15, 3, 1)
    assert summary.load == LoadResult(inserted=11, updated=0, unchanged=0)
    assert summary.extracted == summary.rejected + summary.duplicates + summary.load.total


def test_run_is_recorded_in_audit_tables(ready, raw_dir):
    run_season(ready, "E0", "2425", raw_dir, offline=True)
    row = ready.execute(
        "SELECT status, rows_extracted, rows_rejected, rows_duplicate, rows_loaded "
        "FROM ingestion_runs"
    ).fetchone()
    assert row == ("succeeded", 15, 3, 1, 11)
    assert ready.execute("SELECT count(*) FROM rejected_rows").fetchone()[0] == 3


def test_second_run_is_idempotent(ready, raw_dir):
    run_season(ready, "E0", "2425", raw_dir, offline=True)
    again = run_season(ready, "E0", "2425", raw_dir, offline=True)
    assert again.load == LoadResult(inserted=0, updated=0, unchanged=11)
    assert ready.execute("SELECT count(*) FROM matches").fetchone()[0] == 11


def test_missing_season_is_skipped_not_fatal(ready, tmp_path):
    summary = run_season(ready, "E0", "2425", tmp_path, offline=True)
    assert summary.status == "skipped"
    assert ready.execute("SELECT status FROM ingestion_runs").fetchone()[0] == "skipped"


def test_failure_rolls_back_the_load_but_keeps_the_audit_row(ready, raw_dir, monkeypatch):
    def explode(conn):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(pipeline, "upsert_matches_from_staging", explode)
    with pytest.raises(RuntimeError, match="disk on fire"):
        run_season(ready, "E0", "2425", raw_dir, offline=True)

    assert ready.execute("SELECT count(*) FROM matches").fetchone()[0] == 0
    assert ready.execute("SELECT count(*) FROM teams").fetchone()[0] == 0
    status, error = ready.execute("SELECT status, error_message FROM ingestion_runs").fetchone()
    assert status == "failed" and "disk on fire" in error


def test_run_all_covers_every_combination(conn, raw_dir):
    summaries = pipeline.run_all(conn, ["E0", "E1"], ["2425"], raw_dir, offline=True)
    assert [(s.league_code, s.status) for s in summaries] == [
        ("E0", "succeeded"),
        ("E1", "skipped"),
    ]
    assert conn.execute("SELECT count(*) FROM leagues").fetchone()[0] > 0


def test_run_all_continues_after_a_failure(conn, raw_dir, monkeypatch):
    real = pipeline.extract_season

    def flaky(season, league, *args, **kwargs):
        if league == "E0":
            raise ValueError("corrupt file")
        return real(season, league, *args, **kwargs)

    monkeypatch.setattr(pipeline, "extract_season", flaky)
    (raw_dir / "E1_2425.csv").write_bytes((raw_dir / "E0_2425.csv").read_bytes())
    summaries = pipeline.run_all(conn, ["E0", "E1"], ["2425"], raw_dir, offline=True)
    assert [s.status for s in summaries] == ["failed", "succeeded"]
    assert "corrupt file" in summaries[0].error
