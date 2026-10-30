"""Plotly figure builders. Pure functions of DataFrames, so they are easy to test.

Colours are the validated categorical palette (fixed order, never cycled). Light-mode contrast for
some hues is below 3:1, so every chart is direct-labelled and the dashboard shows a table too.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
MUTED = "rgba(128,128,128,0.35)"
LAYOUT = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "margin": {"l": 48, "r": 110, "t": 40, "b": 40},
    "hovermode": "closest",
    "legend": {"orientation": "h", "y": -0.2},
}


def spread_labels(values: list[float], min_gap: float) -> list[float]:
    """Nudge label positions apart so neighbours are at least ``min_gap`` apart.

    Keeps the original order; used so line-end labels do not overprint each other.
    """
    order = sorted(range(len(values)), key=lambda i: values[i])
    placed = [values[i] for i in order]
    for j in range(1, len(placed)):
        placed[j] = max(placed[j], placed[j - 1] + min_gap)
    result = [0.0] * len(values)
    for pos, i in enumerate(order):
        result[i] = placed[pos]
    return result


def points_race_figure(progression: pd.DataFrame, highlight: int = 6) -> go.Figure:
    """Cumulative points by matchweek. The top ``highlight`` teams are coloured and labelled;
    the rest are thin grey context lines."""
    fig = go.Figure()
    if progression.empty:
        return fig.update_layout(title="No data", **LAYOUT)
    final = progression.groupby("team")["cumulative_points"].max().sort_values(ascending=False)
    leaders = list(final.index[:highlight])
    for team in final.index[highlight:]:
        part = progression[progression["team"] == team]
        fig.add_scatter(
            x=part["matchweek"], y=part["cumulative_points"], name=team, mode="lines",
            line={"color": MUTED, "width": 1}, showlegend=False,
            hovertemplate=f"{team}<br>Week %{{x}}: %{{y}} pts<extra></extra>",
        )  # fmt: skip
    ends = [
        float(progression[progression["team"] == t].sort_values("matchweek").iloc[-1, 2])
        for t in leaders
    ]
    label_y = spread_labels(ends, min_gap=0.05 * float(final.iloc[0]))
    for color, team, y_label in zip(SERIES, leaders, label_y, strict=False):
        part = progression[progression["team"] == team].sort_values("matchweek")
        fig.add_scatter(
            x=part["matchweek"], y=part["cumulative_points"], name=team, mode="lines",
            line={"color": color, "width": 2},
            hovertemplate=f"{team}<br>Week %{{x}}: %{{y}} pts<extra></extra>",
        )  # fmt: skip
        fig.add_annotation(
            x=part["matchweek"].iloc[-1], y=y_label, text=team,
            showarrow=False, xanchor="left", xshift=6, font={"size": 11},
        )  # fmt: skip
    return fig.update_layout(
        title="Points race", xaxis_title="Matchweek", yaxis_title="Points", **LAYOUT
    )


def result_split_figure(summaries: pd.DataFrame) -> go.Figure:
    """Home / draw / away share of results per season, as stacked bars summing to 100%."""
    fig = go.Figure()
    for color, (col, label) in zip(
        SERIES,
        [("home_win_pct", "Home win"), ("draw_pct", "Draw"), ("away_win_pct", "Away win")],
        strict=False,
    ):
        fig.add_bar(
            x=summaries["season"], y=summaries[col].astype(float), name=label,
            marker={"color": color, "line": {"width": 2, "color": "rgba(0,0,0,0)"}},
            hovertemplate=f"{label}<br>%{{x}}: %{{y:.1f}}%<extra></extra>",
        )  # fmt: skip
    return fig.update_layout(
        barmode="stack", title="Home advantage by season", yaxis_title="% of matches",
        xaxis={"type": "category", "title": "Season"}, **LAYOUT,
    )  # fmt: skip


def standout_teams(table: pd.DataFrame, n: int = 3) -> set[str]:
    """Teams worth a permanent label: the best and worst by goal difference, and top scorers."""
    by_gd = table.assign(gd=table["goals_for"] - table["goals_against"]).sort_values("gd")
    top_scorers = table.nlargest(1, "goals_for")["team"]
    return set(by_gd["team"].head(n)) | set(by_gd["team"].tail(n)) | set(top_scorers)


def attack_defence_figure(table: pd.DataFrame) -> go.Figure:
    """Goals scored vs conceded per team, with league-average reference lines."""
    fig = go.Figure()
    if table.empty:
        return fig.update_layout(title="No data", **LAYOUT)
    standouts = standout_teams(table)
    fig.add_scatter(
        x=table["goals_against"], y=table["goals_for"], mode="markers+text",
        text=[t if t in standouts else "" for t in table["team"]],
        customdata=table["team"],
        textposition="top center", textfont={"size": 10},
        marker={"color": SERIES[0], "size": 10, "line": {"width": 2, "color": "rgba(0,0,0,0)"}},
        hovertemplate="%{customdata}<br>Scored %{y}, conceded %{x}<extra></extra>",
        showlegend=False,
    )  # fmt: skip
    fig.add_vline(x=table["goals_against"].mean(), line={"dash": "dot", "color": MUTED})
    fig.add_hline(y=table["goals_for"].mean(), line={"dash": "dot", "color": MUTED})
    # Fewer goals conceded is better, so flip the x-axis: top-right = strong attack AND defence.
    return fig.update_layout(
        title="Attack vs defence", xaxis_title="Goals conceded (better →)",
        yaxis_title="Goals scored", xaxis_autorange="reversed", **LAYOUT,
    )  # fmt: skip
