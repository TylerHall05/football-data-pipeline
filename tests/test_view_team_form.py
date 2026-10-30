import datetime as dt

import pytest


@pytest.fixture
def seven_games(conn):
    """Team A plays B seven times: results W W W D L W W (oldest -> newest)."""
    conn.execute("INSERT INTO leagues VALUES ('E0', 'Premier League', 'England')")
    conn.execute("INSERT INTO teams (name) VALUES ('A'), ('B')")
    a, b = (r[0] for r in conn.execute("SELECT team_id FROM teams ORDER BY name").fetchall())
    scores = [(2, 0), (1, 0), (3, 1), (1, 1), (0, 2), (2, 1), (4, 0)]
    for i, (hg, ag) in enumerate(scores):
        result = "H" if hg > ag else "A" if hg < ag else "D"
        conn.execute(
            "INSERT INTO matches (league_code, season, match_date, home_team_id, away_team_id,"
            " home_goals, away_goals, result) VALUES ('E0', '2425', %s, %s, %s, %s, %s, %s)",
            (dt.date(2024, 9, 1) + dt.timedelta(days=7 * i), a, b, hg, ag, result),
        )
    return conn


def test_only_the_last_five_games_count(seven_games):
    games, form = seven_games.execute(
        "SELECT games, form FROM v_team_form WHERE team = 'A'"
    ).fetchone()
    assert games == 5
    assert form == "WDLWW"  # games 3-7; the first two wins have dropped out


def test_points_and_goals_cover_the_window(seven_games):
    row = seven_games.execute(
        "SELECT points_last_5, goals_for, goals_against FROM v_team_form WHERE team = 'A'"
    ).fetchone()
    assert row == (10, 10, 5)  # 3+1+0+3+3 points; goals 3+1+0+2+4 for, 1+1+2+1+0 against


def test_opponent_form_is_mirrored(seven_games):
    assert seven_games.execute("SELECT form FROM v_team_form WHERE team = 'B'").fetchone()[0] == (
        "LDWLL"
    )


def test_short_history_gives_a_short_form_string(loaded):
    form = loaded.execute("SELECT form FROM v_team_form WHERE team = 'Man United'").fetchone()[0]
    assert form == "WL"  # beat Fulham on 16 Aug, lost to Liverpool on 31 Aug
