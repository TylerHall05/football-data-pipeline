import pytest

from football_pipeline import cli
from football_pipeline.extract import raw_path


def test_parser_defaults():
    args = cli.build_parser().parse_args(["run"])
    assert (args.leagues, args.recent, args.offline) == (["E0"], 3, False)


def test_seasons_and_recent_are_mutually_exclusive():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["run", "--seasons", "2425", "--recent", "2"])


def test_unknown_league_is_a_usage_error(capsys):
    assert cli.main(["run", "--leagues", "ZZ9"]) == 2
    assert "Unknown league" in capsys.readouterr().err


def test_end_to_end_offline_run(db_url, tmp_path, sample_csv_bytes, capsys, monkeypatch):
    import psycopg

    schema = "cli_test"
    with psycopg.connect(db_url, autocommit=True) as admin:
        admin.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        admin.execute(f"CREATE SCHEMA {schema}")
    sep = "&" if "?" in db_url else "?"
    monkeypatch.setenv("DATABASE_URL", f"{db_url}{sep}options=-csearch_path%3D{schema}")
    raw_path(tmp_path, "2425", "E0").write_bytes(sample_csv_bytes)
    try:
        code = cli.main(["run", "--seasons", "2425", "--raw-dir", str(tmp_path), "--offline"])
        out = capsys.readouterr().out
        assert code == 0
        assert "succeeded" in out and "E0" in out
        with psycopg.connect(db_url, options=f"-c search_path={schema}") as check:
            assert check.execute("SELECT count(*) FROM matches").fetchone()[0] == 11
    finally:
        with psycopg.connect(db_url, autocommit=True) as admin:
            admin.execute(f"DROP SCHEMA {schema} CASCADE")
