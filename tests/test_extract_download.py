import pytest
import requests

from football_pipeline.extract import SeasonNotAvailable, download_csv


class FakeResponse:
    def __init__(self, status_code=200, content=b""):
        self.status_code = status_code
        self.content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


class FakeSession:
    """Returns queued responses (or raises queued exceptions) in order."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def get(self, url, timeout=None):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_returns_body_on_success():
    session = FakeSession(FakeResponse(200, b"a,b\n1,2\n"))
    assert download_csv("http://x", session=session) == b"a,b\n1,2\n"
    assert session.calls == 1


def test_404_raises_season_not_available_without_retry():
    session = FakeSession(FakeResponse(404))
    with pytest.raises(SeasonNotAvailable):
        download_csv("http://x", session=session)
    assert session.calls == 1


def test_retries_server_errors_then_succeeds():
    session = FakeSession(
        FakeResponse(503), requests.ConnectionError("boom"), FakeResponse(200, b"ok")
    )
    assert download_csv("http://x", session=session, backoff=0) == b"ok"
    assert session.calls == 3


def test_gives_up_after_max_retries():
    session = FakeSession(FakeResponse(500), FakeResponse(500), FakeResponse(500))
    with pytest.raises(RuntimeError, match="after 3 attempts"):
        download_csv("http://x", session=session, backoff=0)
    assert session.calls == 3


def test_client_errors_other_than_404_are_not_retried():
    session = FakeSession(FakeResponse(403))
    with pytest.raises(requests.HTTPError):
        download_csv("http://x", session=session, backoff=0)
    assert session.calls == 1
