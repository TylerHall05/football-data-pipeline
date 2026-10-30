import pandas as pd

from football_pipeline import charts


def _progression(n_teams=8, weeks=5):
    rows = [
        (f"T{t}", w, (t + 1) * w)  # team t earns t+1 points a week, so T7 leads
        for t in range(n_teams)
        for w in range(1, weeks + 1)
    ]
    return pd.DataFrame(rows, columns=["team", "matchweek", "cumulative_points"])


def test_points_race_highlights_only_the_leaders():
    fig = charts.points_race_figure(_progression(), highlight=3)
    coloured = [t for t in fig.data if t.showlegend is not False]
    assert [t.name for t in coloured] == ["T7", "T6", "T5"]
    assert len(fig.data) == 8  # leaders plus grey context lines
    assert len(fig.layout.annotations) == 3  # direct labels on line ends


def test_leaders_use_palette_colours_in_fixed_order():
    fig = charts.points_race_figure(_progression(), highlight=2)
    colours = [t.line.color for t in fig.data if t.showlegend is not False]
    assert colours == charts.SERIES[:2]


def test_empty_inputs_give_an_empty_figure_not_an_error():
    assert charts.points_race_figure(pd.DataFrame()).layout.title.text == "No data"
    assert charts.attack_defence_figure(pd.DataFrame()).layout.title.text == "No data"


def test_result_split_has_three_stacked_series():
    summaries = pd.DataFrame(
        {"season": ["2324", "2425"], "home_win_pct": [45.0, 42.0],
         "draw_pct": [25.0, 26.0], "away_win_pct": [30.0, 32.0]}
    )  # fmt: skip
    fig = charts.result_split_figure(summaries)
    assert [t.name for t in fig.data] == ["Home win", "Draw", "Away win"]
    assert fig.layout.barmode == "stack"


def test_attack_defence_axis_is_flipped_so_top_right_is_best():
    table = pd.DataFrame({"team": ["A", "B"], "goals_for": [50, 30], "goals_against": [20, 40]})
    fig = charts.attack_defence_figure(table)
    assert fig.layout.xaxis.autorange == "reversed"
    assert list(fig.data[0].customdata) == ["A", "B"]  # hover always has the full name


def test_spread_labels_enforces_a_minimum_gap_and_keeps_order():
    out = charts.spread_labels([80.0, 79.0, 78.5, 60.0], min_gap=3.0)
    assert all(b - a >= 3.0 - 1e-9 for a, b in zip(sorted(out), sorted(out)[1:], strict=False))
    assert out[3] == 60.0  # an isolated label is not moved
    assert out[0] > out[1] > out[2]  # ordering preserved


def test_only_standout_teams_get_permanent_labels():
    table = pd.DataFrame(
        {"team": [f"T{i}" for i in range(20)], "goals_for": range(20), "goals_against": [10] * 20}
    )
    labelled = [t for t in charts.attack_defence_figure(table).data[0].text if t]
    assert 0 < len(labelled) <= 7 < 20
