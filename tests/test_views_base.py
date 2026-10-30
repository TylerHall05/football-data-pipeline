import pytest

from football_pipeline.load import (
    load_leagues,
    stage_matches,
    upsert_matches_from_staging,
    upsert_teams_from_staging,
)


@pytest.fixture
def loaded(conn, clean_matches):
    load_leagues(conn)
    stage_matches(conn, clean_matches)
    upsert_teams_from_staging(conn)
    upsert_matches_from_staging(conn)
    return conn


def test_match_results_has_team_names(loaded):
    row = loaded.execute(
        "SELECT home_team, away_team, home_goals, away_goals FROM v_match_results "
        "WHERE home_team = 'Tottenham'"
    ).fetchone()
    assert row == ("Tottenham", "Everton", 4, 0)


def test_team_matches_doubles_the_rows(loaded):
    n_matches = loaded.execute("SELECT count(*) FROM matches").fetchone()[0]
    assert loaded.execute("SELECT count(*) FROM v_team_matches").fetchone()[0] == 2 * n_matches


def test_points_follow_the_result(loaded):
    rows = dict(
        loaded.execute(
            "SELECT team, points FROM v_team_matches WHERE opponent = 'Everton' "
            "AND match_date = '2024-08-24'"
        ).fetchall()
    )
    assert rows == {"Tottenham": 3}
    loser = loaded.execute(
        "SELECT points, goals_for, goals_against, is_home FROM v_team_matches "
        "WHERE team = 'Everton' AND opponent = 'Tottenham'"
    ).fetchone()
    assert loser == (0, 0, 4, False)


def test_every_match_distributes_two_to_three_points(loaded):
    totals = loaded.execute(
        "SELECT match_id, sum(points) FROM v_team_matches GROUP BY match_id"
    ).fetchall()
    assert totals and all(total in (2, 3) for _, total in totals)
