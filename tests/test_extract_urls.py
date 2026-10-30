import pytest

from football_pipeline.extract import raw_path, season_url, validate_season


def test_season_url():
    assert season_url("2526", "E0") == "https://www.football-data.co.uk/mmz4281/2526/E0.csv"


@pytest.mark.parametrize("bad", ["2025", "25", "2627x", "2528", "abcd", ""])
def test_invalid_season_codes_rejected(bad):
    with pytest.raises(ValueError):
        validate_season(bad)


def test_century_rollover_is_valid():
    assert validate_season("9900") == "9900"


def test_raw_path(tmp_path):
    assert raw_path(tmp_path, "2526", "E0") == tmp_path / "E0_2526.csv"
