from datetime import UTC, datetime

import pytest

from hoerspiel_discovery.enrichment.itunes_coverage import (
    ItunesSearchClient,
    SeriesProbe,
    analyze_probe,
    build_coverage_report,
    normalize,
    publish_report,
)


PROBE = SeriesProbe(
    "die-drei-fragezeichen",
    "Die drei ???",
    "Die drei Fragezeichen",
    ("Die drei ???",),
)


def album(identifier, title, artist="Die drei ???", year="2020"):
    return {
        "collectionId": identifier,
        "collectionName": title,
        "artistName": artist,
        "releaseDate": f"{year}-01-01T00:00:00Z",
        "trackCount": 20,
        "collectionViewUrl": f"https://music.apple.com/de/album/{identifier}",
    }


def test_normalize_handles_umlauts_and_punctuation():
    assert normalize("Die drei ??? – Überfall!") == "die drei uberfall"


def test_analysis_filters_false_positives_and_counts_numbers():
    payload = {
        "results": [
            album(1, "Folge 1: Der Super-Papagei"),
            album(2, "Folge 1: Der Super-Papagei", year="2021"),
            album(3, "Unrelated", artist="Other Artist"),
        ]
    }
    result = analyze_probe(PROBE, payload)
    assert result["candidate_count"] == 2
    assert result["numbered_count"] == 2
    assert result["distinct_episode_numbers"] == 1
    assert result["duplicate_title_groups"] == 1
    assert result["earliest_year"] == 2020


class FakeResponse:
    def __init__(self, status_code, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload or {"results": []}
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def test_client_retries_rate_limit(monkeypatch):
    session = FakeSession(
        [
            FakeResponse(429, headers={"Retry-After": "0"}),
            FakeResponse(200, {"results": [album(1, "Folge 1: Test")]}),
        ]
    )
    sleeps = []
    client = ItunesSearchClient(session=session, sleep=sleeps.append, clock=lambda: 1.0)
    payload = client.search_albums("test")
    assert len(payload["results"]) == 1
    assert len(session.calls) == 2
    assert session.calls[0][1]["verify"].endswith("cacert.pem")
    assert sleeps[0] == 0
    assert sleeps[1] == pytest.approx(3.1)


class FakeClient:
    def search_albums(self, term):
        return {"results": [album(1, "Folge 1: Test")]}


def test_report_is_deterministic_except_timestamp(monkeypatch):
    fixed = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)

    class FixedDatetime:
        @classmethod
        def now(cls, tz):
            return fixed

    monkeypatch.setattr(
        "hoerspiel_discovery.enrichment.itunes_coverage.datetime", FixedDatetime
    )
    first = build_coverage_report(FakeClient(), (PROBE,))
    second = build_coverage_report(FakeClient(), (PROBE,))
    assert first == second
    assert first["summary"]["candidate_results"] == 1


def test_publish_never_overwrites_timestamped_report(tmp_path):
    report = build_coverage_report(FakeClient(), (PROBE,))
    path = publish_report(report, tmp_path)
    assert path.exists()
    assert (tmp_path / "latest.json").exists()
    with pytest.raises(FileExistsError):
        publish_report(report, tmp_path)
