import pandas as pd
import pytest

from football_pipeline.transform import INT_COLUMNS, OUTPUT_COLUMNS
from football_pipeline.validate import validate_matches


def make_frame(**overrides) -> pd.DataFrame:
    """One otherwise-valid cleaned match row, with column overrides applied."""
    row = dict.fromkeys(OUTPUT_COLUMNS)
    row.update(
        league_code="E0",
        season="2425",
        match_date=pd.Timestamp("2024-08-17"),
        home_team="Arsenal",
        away_team="Wolves",
        home_goals=2,
        away_goals=0,
        result="H",
    )
    row.update(overrides)
    frame = pd.DataFrame([row])
    for col in INT_COLUMNS:
        frame[col] = frame[col].astype("Int64")
    return frame


def reason_for(**overrides) -> str:
    valid, rejected = validate_matches(make_frame(**overrides))
    assert len(valid) + len(rejected) == 1
    return rejected["reject_reason"].iloc[0] if len(rejected) else ""


def test_valid_row_passes():
    valid, rejected = validate_matches(make_frame())
    assert len(valid) == 1
    assert rejected.empty
    assert "reject_reason" not in valid.columns


@pytest.mark.parametrize("column", ["match_date", "home_team", "away_team", "home_goals", "result"])
def test_missing_required_field_rejected(column):
    frame = make_frame()
    frame[column] = pd.array([pd.NA], dtype="Int64") if column in INT_COLUMNS else None
    valid, rejected = validate_matches(frame)
    assert valid.empty
    assert rejected["reject_reason"].iloc[0] == "missing_required_field"


def test_invalid_result_code():
    assert reason_for(result="X") == "invalid_result_code"


def test_same_team_on_both_sides():
    assert reason_for(away_team="Arsenal") == "same_team_both_sides"


def test_goals_out_of_range():
    assert reason_for(home_goals=25) == "goals_out_of_range"
    assert reason_for(home_goals=-1, away_goals=0, result="A") == "goals_out_of_range"


def test_result_must_match_score():
    assert reason_for(home_goals=1, away_goals=1, result="H") == "result_contradicts_score"
    assert reason_for(home_goals=0, away_goals=1, result="A") == ""


def test_negative_stat_rejected():
    assert reason_for(home_shots=-3) == "negative_stat"


def test_multiple_reasons_are_joined():
    reason = reason_for(away_team="Arsenal", result="X")
    assert reason == "invalid_result_code;same_team_both_sides"
