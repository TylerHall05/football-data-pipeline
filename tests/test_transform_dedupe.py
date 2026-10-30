import pandas as pd

from football_pipeline.extract import parse_raw_csv
from football_pipeline.transform import deduplicate, transform_matches
from football_pipeline.validate import validate_matches


def test_repeated_fixture_is_removed(sample_csv_bytes):
    cleaned = transform_matches(parse_raw_csv(sample_csv_bytes, "2425", "E0"))
    valid, _ = validate_matches(cleaned)
    deduped, removed = deduplicate(valid)
    assert removed == 1  # Arsenal v Wolves appears twice in the fixture
    assert len(deduped) == len(valid) - 1


def test_keeps_last_occurrence_and_resets_index():
    base = {
        "league_code": "E0",
        "season": "2425",
        "match_date": pd.Timestamp("2024-08-17"),
        "home_team": "Arsenal",
        "away_team": "Wolves",
    }
    df = pd.DataFrame([{**base, "home_goals": 1}, {**base, "home_goals": 2}])
    deduped, removed = deduplicate(df)
    assert removed == 1
    assert list(deduped["home_goals"]) == [2]
    assert list(deduped.index) == [0]
