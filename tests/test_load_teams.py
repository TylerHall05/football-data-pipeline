from football_pipeline.load import stage_matches, upsert_teams_from_staging


def test_every_team_in_staging_is_inserted_once(conn, clean_matches):
    stage_matches(conn, clean_matches)
    expected = set(clean_matches["home_team"]) | set(clean_matches["away_team"])
    assert upsert_teams_from_staging(conn) == len(expected)
    stored = {r[0] for r in conn.execute("SELECT name FROM teams").fetchall()}
    assert stored == expected


def test_existing_teams_are_not_duplicated(conn, clean_matches):
    stage_matches(conn, clean_matches)
    upsert_teams_from_staging(conn)
    assert upsert_teams_from_staging(conn) == 0
    n_teams = conn.execute("SELECT count(*) FROM teams").fetchone()[0]
    assert n_teams == conn.execute("SELECT count(DISTINCT name) FROM teams").fetchone()[0]
