import pandas as pd

from football_pipeline.transform import clean_kickoff_time, parse_dates


def test_parses_four_and_two_digit_years():
    out = parse_dates(pd.Series(["17/08/2024", "31/08/24", " 01/09/2024 "]))
    assert list(out.dt.strftime("%Y-%m-%d")) == ["2024-08-17", "2024-08-31", "2024-09-01"]


def test_is_day_first_not_month_first():
    assert parse_dates(pd.Series(["03/02/2025"])).iloc[0] == pd.Timestamp("2025-02-03")


def test_invalid_and_missing_become_nat():
    out = parse_dates(pd.Series(["not a date", None, "31/02/2024"]))
    assert out.isna().all()


def test_kickoff_time_normalised():
    out = clean_kickoff_time(pd.Series(["20:00", " 9:30", "25:00", "noon", None]))
    assert out.iloc[0] == "20:00"
    assert out.iloc[1] == "09:30"
    assert out.iloc[2:].isna().all()
