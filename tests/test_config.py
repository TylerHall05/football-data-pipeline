from datetime import date

from football_pipeline import config


def test_season_code_pads_and_wraps_century():
    assert config.season_code(2025) == "2526"
    assert config.season_code(2008) == "0809"
    assert config.season_code(1999) == "9900"


def test_current_season_before_and_after_july():
    assert config.current_season_code(date(2026, 10, 30)) == "2627"
    assert config.current_season_code(date(2026, 3, 1)) == "2526"
    assert config.current_season_code(date(2026, 7, 1)) == "2627"
    assert config.current_season_code(date(2026, 6, 30)) == "2526"


def test_recent_seasons_oldest_first():
    assert config.recent_seasons(3, date(2026, 10, 30)) == ["2425", "2526", "2627"]


def test_database_url_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db:5432/x")
    assert config.get_database_url() == "postgresql://u:p@db:5432/x"
    monkeypatch.delenv("DATABASE_URL")
    assert config.get_database_url() == config.DEFAULT_DATABASE_URL
