"""Read-side API: parameterised queries over the analytical views, returned as DataFrames."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import psycopg


def _frame(conn: psycopg.Connection, sql: str, params: Sequence[object] = ()) -> pd.DataFrame:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        columns = [col.name for col in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=columns)


def available_seasons(conn: psycopg.Connection) -> pd.DataFrame:
    """Leagues and seasons that have data, newest season first."""
    return _frame(
        conn,
        """SELECT s.league_code, l.name AS league_name, s.season, s.matches
           FROM v_season_summary s JOIN leagues l USING (league_code)
           ORDER BY s.season DESC, l.name""",
    )


def league_table(conn: psycopg.Connection, league_code: str, season: str) -> pd.DataFrame:
    return _frame(
        conn,
        """SELECT position, team, played, won, drawn, lost, goals_for, goals_against,
                  goal_difference, points
           FROM v_league_table WHERE league_code = %s AND season = %s
           ORDER BY position, team""",
        (league_code, season),
    )


def team_form(conn: psycopg.Connection, league_code: str, season: str) -> pd.DataFrame:
    return _frame(
        conn,
        """SELECT team, form, points_last_5 FROM v_team_form
           WHERE league_code = %s AND season = %s
           ORDER BY points_last_5 DESC, team""",
        (league_code, season),
    )


def season_summaries(conn: psycopg.Connection, league_code: str) -> pd.DataFrame:
    """One row per season for a league, oldest first (for trend charts)."""
    return _frame(
        conn,
        "SELECT * FROM v_season_summary WHERE league_code = %s ORDER BY season",
        (league_code,),
    )


def points_progression(
    conn: psycopg.Connection, league_code: str, season: str, teams: Sequence[str] | None = None
) -> pd.DataFrame:
    """Cumulative points by matchweek, optionally restricted to some teams."""
    sql = """SELECT team, matchweek, cumulative_points FROM v_points_progression
             WHERE league_code = %s AND season = %s"""
    params: list[object] = [league_code, season]
    if teams is not None:
        sql += " AND team = ANY(%s)"
        params.append(list(teams))
    return _frame(conn, sql + " ORDER BY team, matchweek", params)
