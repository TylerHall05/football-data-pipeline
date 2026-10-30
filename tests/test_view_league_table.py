import pandas as pd


def _expected_table(matches: pd.DataFrame) -> pd.DataFrame:
    """Independent pandas implementation, used to cross-check the SQL view."""
    home = matches.rename(columns={"home_team": "team", "home_goals": "gf", "away_goals": "ga"})
    away = matches.rename(columns={"away_team": "team", "away_goals": "gf", "home_goals": "ga"})
    long = pd.concat([home[["team", "gf", "ga"]], away[["team", "gf", "ga"]]])
    long["pts"] = (long["gf"] > long["ga"]) * 3 + (long["gf"] == long["ga"]) * 1
    grouped = long.groupby("team").agg(
        played=("pts", "size"), gf=("gf", "sum"), ga=("ga", "sum"), pts=("pts", "sum")
    )
    return grouped.astype(int)


def test_totals_match_an_independent_calculation(loaded, clean_matches):
    expected = _expected_table(clean_matches)
    rows = loaded.execute(
        "SELECT team, played, goals_for, goals_against, points FROM v_league_table"
    ).fetchall()
    actual = {team: {"played": p, "gf": gf, "ga": ga, "pts": pts} for team, p, gf, ga, pts in rows}
    assert actual == expected.to_dict("index")


def test_positions_follow_points(loaded):
    rows = loaded.execute(
        "SELECT position, points FROM v_league_table ORDER BY position, team"
    ).fetchall()
    points = [p for _, p in rows]
    assert points == sorted(points, reverse=True)
    assert rows[0][0] == 1


def test_won_drawn_lost_add_up_to_played(loaded):
    bad = loaded.execute("SELECT count(*) FROM v_league_table WHERE won + drawn + lost <> played")
    assert bad.fetchone()[0] == 0


def test_goal_difference_is_for_minus_against(loaded):
    bad = loaded.execute(
        "SELECT count(*) FROM v_league_table WHERE goal_difference <> goals_for - goals_against"
    )
    assert bad.fetchone()[0] == 0
