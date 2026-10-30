import pandas as pd

from football_pipeline.extract import parse_raw_csv
from football_pipeline.transform import transform_matches


def _transformed(sample_csv_bytes: bytes) -> pd.DataFrame:
    return transform_matches(parse_raw_csv(sample_csv_bytes, "2425", "E0"))


def test_blank_trailing_rows_are_dropped(sample_csv_bytes):
    out = _transformed(sample_csv_bytes)
    assert len(out) == 15  # 16 data lines, one of them empty
    assert out["home_team"].notna().sum() == 15


def test_columns_are_typed(sample_csv_bytes):
    out = _transformed(sample_csv_bytes)
    assert pd.api.types.is_datetime64_any_dtype(out["match_date"])
    assert str(out["home_goals"].dtype) == "Int64"
    assert str(out["home_shots"].dtype) == "Int64"


def test_messy_values_are_normalised(sample_csv_bytes):
    out = _transformed(sample_csv_bytes)
    row = out[out["referee"] == "M Oliver"].iloc[0]
    assert row["home_team"] == "Liverpool"  # padding trimmed
    assert row["away_team"] == "Man United"  # double space collapsed
    assert row["match_date"] == pd.Timestamp("2024-08-31")  # dd/mm/yy parsed


def test_unparseable_date_becomes_missing_not_an_error(sample_csv_bytes):
    out = _transformed(sample_csv_bytes)
    assert out["match_date"].isna().sum() == 1
