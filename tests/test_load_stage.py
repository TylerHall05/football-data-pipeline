import datetime as dt

import pandas as pd

from football_pipeline.load import stage_matches, staging_columns


def test_staging_columns_cover_every_transform_output():
    cols = staging_columns()
    assert cols["match_date"] == "date"
    assert cols["home_goals"] == "smallint"
    assert cols["home_team"] == "text"


def test_rows_are_copied_to_staging(conn, clean_matches):
    assert stage_matches(conn, clean_matches) == len(clean_matches) == 11
    assert conn.execute("SELECT count(*) FROM stg_matches").fetchone()[0] == 11


def test_values_survive_the_round_trip(conn, clean_matches):
    stage_matches(conn, clean_matches)
    row = conn.execute(
        "SELECT match_date, kickoff_time, home_goals FROM stg_matches "
        "WHERE home_team = 'Man United' AND away_team = 'Fulham'"
    ).fetchone()
    assert row == (dt.date(2024, 8, 16), dt.time(20, 0), 1)


def test_missing_values_become_sql_null(conn):
    df = pd.DataFrame(
        {
            "league_code": ["E0"],
            "season": ["2425"],
            "match_date": [pd.Timestamp("2024-08-16")],
            "home_team": ["A"],
            "away_team": ["B"],
            "home_goals": pd.array([1], dtype="Int64"),
            "away_goals": pd.array([0], dtype="Int64"),
            "result": ["H"],
            "home_shots": pd.array([pd.NA], dtype="Int64"),
            "referee": pd.array([pd.NA], dtype="string"),
        }
    ).reindex(columns=list(staging_columns()))
    stage_matches(conn, df)
    assert conn.execute("SELECT home_shots, referee FROM stg_matches").fetchone() == (None, None)


def test_staging_can_be_rebuilt_in_one_transaction(conn, clean_matches):
    stage_matches(conn, clean_matches)
    stage_matches(conn, clean_matches.head(3))
    assert conn.execute("SELECT count(*) FROM stg_matches").fetchone()[0] == 3
