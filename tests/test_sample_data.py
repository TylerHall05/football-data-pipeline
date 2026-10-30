import pandas as pd
import pytest

from football_pipeline import pipeline
from football_pipeline.sample_data import generate_season, round_robin, write_sample_files


def test_round_robin_every_pair_meets_once():
    teams = [f"T{i}" for i in range(20)]
    fixtures = [pair for rnd in round_robin(teams) for pair in rnd]
    assert len(fixtures) == 190  # 20 * 19 / 2
    assert len({frozenset(p) for p in fixtures}) == 190
    for rnd in round_robin(teams):  # nobody plays twice in a round
        assert len({t for pair in rnd for t in pair}) == 20


def test_season_has_380_matches_and_each_pairing_twice():
    df = generate_season("E0", "2425")
    assert len(df) == 380
    assert df.groupby(["HomeTeam", "AwayTeam"]).size().eq(1).all()
    assert df["HomeTeam"].nunique() == 20


def test_generation_is_reproducible_and_seed_sensitive():
    pd.testing.assert_frame_equal(
        generate_season("E0", "2425", 1), generate_season("E0", "2425", 1)
    )
    assert not generate_season("E0", "2425", 1).equals(generate_season("E0", "2425", 2))


def test_results_agree_with_scores():
    df = generate_season("E0", "2425")
    implied = (
        (df["FTHG"] > df["FTAG"])
        .map({True: "H"})
        .fillna((df["FTHG"] < df["FTAG"]).map({True: "A", False: "D"}))
    )
    assert (implied == df["FTR"]).all()


def test_unknown_league_is_rejected():
    with pytest.raises(ValueError, match="No synthetic teams"):
        generate_season("ZZ9", "2425")


def test_generated_season_loads_cleanly_end_to_end(conn, tmp_path):
    write_sample_files(["E0"], ["2425"], tmp_path)
    (summary,) = pipeline.run_all(conn, ["E0"], ["2425"], tmp_path, offline=True)
    assert summary.status == "succeeded"
    assert (summary.extracted, summary.rejected, summary.duplicates) == (380, 0, 0)
    assert summary.load.inserted == 380
