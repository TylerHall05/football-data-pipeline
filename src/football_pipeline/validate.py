"""Data-quality rules. Failing rows are quarantined with a reason, never silently dropped."""

from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = [
    "match_date",
    "home_team",
    "away_team",
    "home_goals",
    "away_goals",
    "result",
]
STAT_COLUMNS = [
    "home_shots",
    "away_shots",
    "home_shots_on_target",
    "away_shots_on_target",
    "home_fouls",
    "away_fouls",
    "home_corners",
    "away_corners",
    "home_yellows",
    "away_yellows",
    "home_reds",
    "away_reds",
]
MAX_PLAUSIBLE_GOALS = 20
VALID_RESULTS = {"H", "D", "A"}


def _false_if_na(mask: pd.Series) -> pd.Series:
    return mask.fillna(False).astype(bool)


def build_rule_masks(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Boolean mask per rule; True marks a row that VIOLATES the rule."""
    missing = df[REQUIRED_COLUMNS].isna().any(axis=1)
    home = df["home_goals"].astype("float64")
    away = df["away_goals"].astype("float64")
    implied = pd.Series(np.select([home > away, home < away], ["H", "A"], "D"), index=df.index)
    goals_out_of_range = (
        (home < 0) | (away < 0) | (home > MAX_PLAUSIBLE_GOALS) | (away > MAX_PLAUSIBLE_GOALS)
    )
    negative_stat = pd.concat([df[c] < 0 for c in STAT_COLUMNS], axis=1).any(axis=1)

    return {
        "missing_required_field": missing,
        "invalid_result_code": ~df["result"].isin(VALID_RESULTS) & df["result"].notna(),
        "same_team_both_sides": _false_if_na(df["home_team"] == df["away_team"]),
        "goals_out_of_range": _false_if_na(goals_out_of_range),
        # Only meaningful when the code itself is valid; otherwise it just repeats the rule above.
        "result_contradicts_score": (
            ~missing & df["result"].isin(VALID_RESULTS) & (implied != df["result"])
        ),
        "negative_stat": _false_if_na(negative_stat),
    }


def validate_matches(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a cleaned frame into (valid, rejected). Rejected rows carry ``reject_reason``."""
    reasons = pd.Series("", index=df.index, dtype="object")
    for name, mask in build_rule_masks(df).items():
        reasons = reasons.where(~mask, reasons + name + ";")
    failed = reasons != ""
    rejected = df[failed].assign(reject_reason=reasons[failed].str.rstrip(";"))
    return df[~failed].copy(), rejected
