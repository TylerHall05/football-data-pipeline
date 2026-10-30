from football_pipeline.config import LEAGUES
from football_pipeline.load import load_leagues


def test_all_configured_leagues_are_loaded(conn):
    assert load_leagues(conn) == len(LEAGUES)
    rows = dict(conn.execute("SELECT league_code, name FROM leagues").fetchall())
    assert rows["E0"] == "Premier League"
    assert len(rows) == len(LEAGUES)


def test_reloading_updates_instead_of_duplicating(conn):
    load_leagues(conn)
    conn.execute("UPDATE leagues SET name = 'Old name' WHERE league_code = 'E0'")
    load_leagues(conn)
    assert conn.execute("SELECT count(*) FROM leagues").fetchone()[0] == len(LEAGUES)
    assert conn.execute("SELECT name FROM leagues WHERE league_code='E0'").fetchone()[0] == (
        "Premier League"
    )
