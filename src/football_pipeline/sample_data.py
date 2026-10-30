"""Synthetic season generator for offline development, demos and tests.

The files mimic football-data.co.uk's CSV layout, but every score, shot and card is RANDOM.
Team names are real only so the output looks familiar; the results are not real results.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from football_pipeline.extract import raw_path, validate_season

TEAMS: dict[str, list[str]] = {
    "E0": [
        "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton", "Chelsea",
        "Crystal Palace", "Everton", "Fulham", "Ipswich", "Leicester", "Liverpool",
        "Man City", "Man United", "Newcastle", "Nott'm Forest", "Southampton", "Tottenham",
        "West Ham", "Wolves",
    ],
    "SP1": [
        "Alaves", "Ath Bilbao", "Ath Madrid", "Barcelona", "Betis", "Celta", "Espanol",
        "Getafe", "Girona", "Las Palmas", "Leganes", "Mallorca", "Osasuna", "Real Madrid",
        "Sevilla", "Sociedad", "Valencia", "Vallecano", "Valladolid", "Villarreal",
    ],
}  # fmt: skip
REFEREES = ["M Oliver", "A Taylor", "P Tierney", "S Attwell", "C Pawson", "R Jones", "D Coote"]
KICKOFFS = ["12:30", "15:00", "15:00", "15:00", "17:30", "20:00"]
CSV_COLUMNS = [
    "Div", "Date", "Time", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR", "HTHG", "HTAG", "HTR",
    "Referee", "HS", "AS", "HST", "AST", "HF", "AF", "HC", "AC", "HY", "AY", "HR", "AR",
]  # fmt: skip


def round_robin(teams: list[str]) -> list[list[tuple[str, str]]]:
    """Single round-robin schedule (circle method): n-1 rounds of (home, away) pairs."""
    pool = list(teams)
    n = len(pool)
    rounds = []
    for r in range(n - 1):
        pairs = [(pool[i], pool[n - 1 - i]) for i in range(n // 2)]
        # alternate home/away so no team is always at home
        rounds.append([(a, h) if (r + i) % 2 else (h, a) for i, (h, a) in enumerate(pairs)])
        pool = [pool[0], pool[-1], *pool[1:-1]]
    return rounds


def _result(home: int, away: int) -> str:
    return "H" if home > away else "A" if home < away else "D"


def generate_season(league: str, season: str, seed: int = 0) -> pd.DataFrame:
    """One full synthetic double round-robin season in football-data's column layout."""
    if league not in TEAMS:
        raise ValueError(f"No synthetic teams for {league!r}; available: {sorted(TEAMS)}")
    validate_season(season)
    teams = TEAMS[league]
    rng = np.random.default_rng([seed, int(season), sum(map(ord, league))])
    attack = dict(zip(teams, rng.lognormal(0, 0.25, len(teams)), strict=True))
    defence = dict(zip(teams, rng.lognormal(0, 0.25, len(teams)), strict=True))

    first_half = round_robin(teams)
    second_half = [[(a, h) for h, a in rnd] for rnd in first_half]
    start = date(2000 + int(season[:2]), 8, 16)

    rows = []
    for week, rnd in enumerate(first_half + second_half):
        for home, away in rnd:
            hg = int(rng.poisson(1.45 * attack[home] / defence[away]))
            ag = int(rng.poisson(1.10 * attack[away] / defence[home]))
            hth, hta = int(rng.binomial(hg, 0.45)), int(rng.binomial(ag, 0.45))
            hs, as_ = int(rng.poisson(9 + 2.5 * hg)), int(rng.poisson(7 + 2.5 * ag))
            kickoff_day = start + timedelta(days=7 * week + int(rng.integers(0, 3)))
            rows.append(
                [
                    league, kickoff_day.strftime("%d/%m/%Y"), str(rng.choice(KICKOFFS)),
                    home, away, hg, ag, _result(hg, ag), hth, hta, _result(hth, hta),
                    str(rng.choice(REFEREES)), hs, as_,
                    int(rng.binomial(hs, 0.33)), int(rng.binomial(as_, 0.33)),
                    int(rng.poisson(11)), int(rng.poisson(11)),
                    int(rng.poisson(5.5)), int(rng.poisson(4.5)),
                    int(rng.poisson(1.8)), int(rng.poisson(2.0)),
                    int(rng.random() < 0.04), int(rng.random() < 0.05),
                ]
            )  # fmt: skip
    return pd.DataFrame(rows, columns=CSV_COLUMNS)


def write_sample_files(
    league_codes: list[str], seasons: list[str], raw_dir: Path | str, seed: int = 0
) -> list[Path]:
    """Write synthetic CSVs where the extract stage's offline mode expects to find them."""
    written = []
    for season in seasons:
        for league in league_codes:
            path = raw_path(raw_dir, season, league)
            path.parent.mkdir(parents=True, exist_ok=True)
            generate_season(league, season, seed).to_csv(path, index=False)
            written.append(path)
    return written
