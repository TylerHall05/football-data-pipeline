import psycopg
import pytest


@pytest.fixture
def seeded(conn):
    conn.execute("INSERT INTO leagues VALUES ('E0', 'Premier League', 'England')")
    conn.execute("INSERT INTO teams (name) VALUES ('Arsenal'), ('Wolves')")
    ids = dict(conn.execute("SELECT name, team_id FROM teams").fetchall())
    return conn, ids


def _insert(conn, home, away, hg=2, ag=0, result="H", date="2024-08-17"):
    conn.execute(
        """INSERT INTO matches (league_code, season, match_date, home_team_id, away_team_id,
                                home_goals, away_goals, result)
           VALUES ('E0', '2425', %s, %s, %s, %s, %s, %s)""",
        (date, home, away, hg, ag, result),
    )


def test_valid_match_is_accepted(seeded):
    conn, t = seeded
    _insert(conn, t["Arsenal"], t["Wolves"])
    assert conn.execute("SELECT count(*) FROM matches").fetchone()[0] == 1


def test_result_must_agree_with_score(seeded):
    conn, t = seeded
    with pytest.raises(psycopg.errors.CheckViolation):
        _insert(conn, t["Arsenal"], t["Wolves"], hg=2, ag=0, result="A")


def test_team_cannot_play_itself(seeded):
    conn, t = seeded
    with pytest.raises(psycopg.errors.CheckViolation):
        _insert(conn, t["Arsenal"], t["Arsenal"], hg=1, ag=1, result="D")


def test_same_fixture_cannot_be_stored_twice(seeded):
    conn, t = seeded
    _insert(conn, t["Arsenal"], t["Wolves"])
    with pytest.raises(psycopg.errors.UniqueViolation):
        _insert(conn, t["Arsenal"], t["Wolves"])


def test_unknown_team_is_rejected_by_foreign_key(seeded):
    conn, t = seeded
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _insert(conn, t["Arsenal"], 999_999)
