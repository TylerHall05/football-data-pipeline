import pandas as pd

from football_pipeline.transform import clean_result, clean_team_names, to_nullable_int


def test_team_names_trimmed_collapsed_and_aliased():
    out = clean_team_names(pd.Series([" Liverpool ", "Man  United", "Spurs", "", None]))
    assert out.iloc[0] == "Liverpool"
    assert out.iloc[1] == "Man United"
    assert out.iloc[2] == "Tottenham"
    assert out.iloc[3:].isna().all()


def test_result_codes_normalised():
    out = clean_result(pd.Series(["h", " D ", "A", "", None]))
    assert list(out.iloc[:3]) == ["H", "D", "A"]
    assert out.iloc[3:].isna().all()


def test_nullable_int_handles_text_floats_and_junk():
    out = to_nullable_int(pd.Series(["2", "3.0", "1.5", "x", "", None, "-1"]))
    assert str(out.dtype) == "Int64"
    assert out.iloc[0] == 2
    assert out.iloc[1] == 3
    assert out.iloc[2:6].isna().all()
    assert out.iloc[6] == -1  # range checks belong to validation, not coercion
