def test_cumulative_points_grow_match_by_match(loaded):
    rows = loaded.execute(
        "SELECT matchweek, cumulative_points FROM v_points_progression "
        "WHERE team = 'Man United' ORDER BY matchweek"
    ).fetchall()
    assert rows == [(1, 3), (2, 3)]  # won then lost


def test_final_cumulative_points_equal_the_league_table(loaded):
    mismatches = loaded.execute(
        """SELECT count(*) FROM v_league_table t
           JOIN v_points_progression p
             ON p.league_code = t.league_code AND p.season = t.season AND p.team = t.team
            AND p.matchweek = t.played
           WHERE p.cumulative_points <> t.points
              OR p.cumulative_goal_difference <> t.goal_difference"""
    ).fetchone()[0]
    assert mismatches == 0
    # guard against a vacuous pass: the join must actually have produced rows
    assert loaded.execute("SELECT count(*) FROM v_points_progression").fetchone()[0] > 0
