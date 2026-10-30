import os
from pathlib import Path

import psycopg
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from football_pipeline import pipeline
from football_pipeline.db import apply_schema
from football_pipeline.sample_data import write_sample_files

APP = str(Path(__file__).resolve().parents[1] / "dashboard" / "app.py")


@pytest.fixture
def app_schema(db_url, monkeypatch):
    """Point the app at an empty throwaway schema through DATABASE_URL."""
    schema = "dash_test"
    with psycopg.connect(db_url, autocommit=True) as admin:
        admin.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        admin.execute(f"CREATE SCHEMA {schema}")
    sep = "&" if "?" in db_url else "?"
    monkeypatch.setenv("DATABASE_URL", f"{db_url}{sep}options=-csearch_path%3D{schema}")
    st.cache_data.clear()
    yield schema
    st.cache_data.clear()
    with psycopg.connect(db_url, autocommit=True) as admin:
        admin.execute(f"DROP SCHEMA {schema} CASCADE")


def test_dashboard_shows_headline_metrics(app_schema, tmp_path):
    write_sample_files(["E0"], ["2425"], tmp_path)
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        pipeline.run_all(conn, ["E0"], ["2425"], tmp_path, offline=True)
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert dict((m.label, m.value) for m in at.metric)["Matches"] == "380"
    assert [t.label for t in at.tabs] == ["League table", "Points race", "Teams", "Season trends"]


def test_dashboard_explains_an_empty_database(app_schema):
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        apply_schema(conn)
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert "no matches yet" in at.warning[0].value
