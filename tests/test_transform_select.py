import pandas as pd

from football_pipeline.extract import parse_raw_csv
from football_pipeline.transform import OUTPUT_COLUMNS, select_and_rename


def test_renames_and_drops_betting_odds(sample_csv_bytes):
    raw = parse_raw_csv(sample_csv_bytes, "2425", "E0")
    out = select_and_rename(raw)
    assert list(out.columns) == OUTPUT_COLUMNS
    assert "B365H" not in out.columns
    assert out.loc[0, "home_team"] == "Man United"
    assert out.loc[0, "home_goals"] == "1"


def test_missing_columns_become_empty():
    raw = pd.DataFrame(
        {
            "league_code": ["E0"],
            "season": ["0405"],
            "Date": ["14/08/04"],
            "HomeTeam": ["Arsenal"],
            "AwayTeam": ["Everton"],
        }
    )
    out = select_and_rename(raw)
    assert list(out.columns) == OUTPUT_COLUMNS
    assert out["referee"].isna().all()
    assert out["home_shots"].isna().all()
