import pytest

from football_pipeline.extract import SeasonNotAvailable, extract_season, raw_path
from tests.test_extract_download import FakeResponse, FakeSession


def test_online_downloads_caches_and_parses(tmp_path, sample_csv_bytes):
    session = FakeSession(FakeResponse(200, sample_csv_bytes))
    frame = extract_season("2425", "E0", tmp_path, session=session)
    assert len(frame) == 15
    assert raw_path(tmp_path, "2425", "E0").read_bytes() == sample_csv_bytes


def test_offline_reads_from_cache_without_network(tmp_path, sample_csv_bytes):
    raw_path(tmp_path, "2425", "E0").write_bytes(sample_csv_bytes)
    frame = extract_season("2425", "E0", tmp_path, offline=True, session=object())
    assert len(frame) == 15


def test_offline_missing_cache_raises(tmp_path):
    with pytest.raises(SeasonNotAvailable):
        extract_season("2425", "E0", tmp_path, offline=True)


def test_online_404_propagates_and_writes_nothing(tmp_path):
    session = FakeSession(FakeResponse(404))
    with pytest.raises(SeasonNotAvailable):
        extract_season("2627", "E0", tmp_path, session=session)
    assert not raw_path(tmp_path, "2627", "E0").exists()
