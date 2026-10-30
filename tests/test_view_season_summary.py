import pytest


def test_match_count_and_scoring_rate(loaded, clean_matches):
    row = loaded.execute(
        "SELECT matches, goals_per_match FROM v_season_summary WHERE league_code = 'E0'"
    ).fetchone()
    expected = (clean_matches["home_goals"] + clean_matches["away_goals"]).astype(float).mean()
    assert row[0] == len(clean_matches)
    assert float(row[1]) == pytest.approx(expected, abs=0.01)


def test_result_percentages_sum_to_one_hundred(loaded):
    home, draw, away = loaded.execute(
        "SELECT home_win_pct, draw_pct, away_win_pct FROM v_season_summary"
    ).fetchone()
    assert float(home + draw + away) == pytest.approx(100.0, abs=0.2)  # rounding slack


def test_one_row_per_league_and_season(loaded):
    assert loaded.execute("SELECT count(*) FROM v_season_summary").fetchone()[0] == 1
