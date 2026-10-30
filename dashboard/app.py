"""Streamlit dashboard. Run with:  streamlit run dashboard/app.py"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from football_pipeline import charts, queries
from football_pipeline.db import connect

st.set_page_config(page_title="Football pipeline", page_icon="⚽", layout="wide")


@st.cache_data(ttl=300, show_spinner=False)
def load_catalogue() -> tuple[pd.DataFrame, pd.Timestamp | None]:
    with connect() as conn:
        return queries.available_seasons(conn), queries.last_successful_run(conn)


@st.cache_data(ttl=300, show_spinner=False)
def load_season(league: str, season: str) -> dict[str, pd.DataFrame]:
    with connect() as conn:
        return {
            "table": queries.league_table(conn, league, season),
            "form": queries.team_form(conn, league, season),
            "progression": queries.points_progression(conn, league, season),
            "trend": queries.season_summaries(conn, league),
        }


try:
    catalogue, updated = load_catalogue()
except Exception as exc:  # no database / not migrated: tell the user how to fix it
    st.error(f"Could not read the database: {exc}")
    st.info("Start PostgreSQL, set DATABASE_URL, then run `football-pipeline run`.")
    st.stop()

if catalogue.empty:
    st.warning("The database has no matches yet. Run `football-pipeline run` first.")
    st.stop()

st.title("⚽ Football data pipeline")
st.caption(f"Last successful load: {updated:%d %b %Y %H:%M}" if updated is not None else "")

with st.sidebar:
    league_name = st.selectbox("League", sorted(catalogue["league_name"].unique()))
    league_rows = catalogue[catalogue["league_name"] == league_name]
    season = st.selectbox("Season", list(league_rows["season"]))
    league = league_rows["league_code"].iloc[0]

data = load_season(league, season)
current = data["trend"][data["trend"]["season"] == season].iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Matches", int(current["matches"]))
c2.metric("Goals per match", float(current["goals_per_match"]))
c3.metric("Home wins", f"{float(current['home_win_pct']):.1f}%")
c4.metric("Draws", f"{float(current['draw_pct']):.1f}%")

tab_table, tab_race, tab_teams, tab_trends = st.tabs(
    ["League table", "Points race", "Teams", "Season trends"]
)
with tab_table:
    st.dataframe(data["table"], hide_index=True, width="stretch")
with tab_race:
    st.plotly_chart(charts.points_race_figure(data["progression"]), width="stretch")
with tab_teams:
    left, right = st.columns([3, 2])
    left.plotly_chart(charts.attack_defence_figure(data["table"]), width="stretch")
    right.subheader("Form (last 5)")
    right.dataframe(data["form"], hide_index=True, width="stretch")
with tab_trends:
    st.plotly_chart(charts.result_split_figure(data["trend"]), width="stretch")
    st.dataframe(data["trend"], hide_index=True, width="stretch")
