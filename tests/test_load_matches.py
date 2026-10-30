import pytest

from football_pipeline.load import (
    LoadResult,
    load_leagues,
    stage_matches,
    upsert_matches_from_staging,
    upsert_teams_from_staging,
)


def _load(conn, df) -> LoadResult:
    stage_matches(conn, df)
    upsert_teams_from_staging(conn)
    return upsert_matches_from_staging(conn)


@pytest.fixture
def leagues(conn):
    load_leagues(conn)


def test_first_load_inserts_every_row(conn, leagues, clean_matches):
    result = _load(conn, clean_matches)
    assert result == LoadResult(inserted=11, updated=0, unchanged=0)
    assert conn.execute("SELECT count(*) FROM matches").fetchone()[0] == 11


def test_rerunning_the_same_data_changes_nothing(conn, leagues, clean_matches):
    _load(conn, clean_matches)
    again = _load(conn, clean_matches)
    assert again == LoadResult(inserted=0, updated=0, unchanged=11)
    assert conn.execute("SELECT count(*) FROM matches").fetchone()[0] == 11


def test_corrected_source_data_updates_the_stored_row(conn, leagues, clean_matches):
    _load(conn, clean_matches)
    # now() is fixed per transaction, so backdate rows to see which ones the upsert touches.
    conn.execute("UPDATE matches SET updated_at = '2000-01-01'")
    corrected = clean_matches.copy()
    corrected.loc[corrected["home_team"] == "Tottenham", "referee"] = "New Referee"
    result = _load(conn, corrected)
    assert result == LoadResult(inserted=0, updated=1, unchanged=10)
    stored = conn.execute(
        "SELECT referee FROM matches m JOIN teams t ON t.team_id = m.home_team_id "
        "WHERE t.name = 'Tottenham'"
    ).fetchone()[0]
    assert stored == "New Referee"
    touched = conn.execute("SELECT count(*) FROM matches WHERE updated_at > '2000-01-01'")
    assert touched.fetchone()[0] == 1  # unchanged rows were left alone


def test_new_matches_are_added_alongside_existing_ones(conn, leagues, clean_matches):
    _load(conn, clean_matches.head(6))
    result = _load(conn, clean_matches)
    assert result == LoadResult(inserted=5, updated=0, unchanged=6)
