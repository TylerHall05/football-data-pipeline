from football_pipeline import queries


def test_available_seasons_lists_loaded_data(loaded):
    df = queries.available_seasons(loaded)
    assert df.to_dict("records") == [
        {"league_code": "E0", "league_name": "Premier League", "season": "2425", "matches": 11}
    ]


def test_league_table_is_ordered_by_position(loaded):
    df = queries.league_table(loaded, "E0", "2425")
    assert list(df.columns[:3]) == ["position", "team", "played"]
    assert df["position"].is_monotonic_increasing
    assert df["played"].sum() == 22  # 11 matches, two teams each


def test_league_table_for_unknown_season_is_empty(loaded):
    assert queries.league_table(loaded, "E0", "9900").empty


def test_team_form_has_one_row_per_team(loaded):
    df = queries.team_form(loaded, "E0", "2425")
    assert df["team"].is_unique
    assert set(df["form"].str.replace("[WDL]", "", regex=True)) == {""}


def test_points_progression_can_filter_teams(loaded):
    df = queries.points_progression(loaded, "E0", "2425", teams=["Man United", "Arsenal"])
    assert set(df["team"]) == {"Man United", "Arsenal"}
    assert len(queries.points_progression(loaded, "E0", "2425")) == 22


def test_season_summaries_returns_a_row_per_season(loaded):
    assert len(queries.season_summaries(loaded, "E0")) == 1


def test_last_successful_run_is_none_before_any_load(conn):
    assert queries.last_successful_run(conn) is None


def test_last_successful_run_ignores_failures(conn):
    from football_pipeline.audit import finish_run, start_run

    finish_run(conn, start_run(conn, "E0", "2425"), "failed", error_message="x")
    assert queries.last_successful_run(conn) is None
    finish_run(conn, start_run(conn, "E0", "2425"), "succeeded")
    assert queries.last_successful_run(conn) is not None
