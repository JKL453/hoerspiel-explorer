from types import SimpleNamespace

import pytest

from hoerspiel_discovery.scraper.fetch_series import build_file_name
from hoerspiel_discovery.tasks import fetch


def _response(status_code: int, text: str = "") -> SimpleNamespace:
    def raise_for_status() -> None:
        if status_code >= 400:
            raise RuntimeError(f"HTTP {status_code}")

    return SimpleNamespace(
        status_code=status_code,
        content=text.encode("cp1252"),
        raise_for_status=raise_for_status,
    )


def test_decode_hoerspiele_html_uses_windows_1252():
    content = "Änne hört: „Hallo“ – groß!".encode("cp1252")

    assert fetch.decode_hoerspiele_html(content) == "Änne hört: „Hallo“ – groß!"


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (b"Die Prophezeiung erf\x81llt sich", "Die Prophezeiung erfüllt sich"),
        (b"Der Fr\xfc\x81hling ist da", "Der Frühling ist da"),
    ],
)
def test_decode_hoerspiele_html_repairs_known_0x81_anomaly(content, expected):
    assert fetch.decode_hoerspiele_html(content) == expected


def test_fetch_episode_page_saves_html(monkeypatch, tmp_path):
    monkeypatch.setattr(fetch, "DETAIL_PAGES_DIR", tmp_path)
    monkeypatch.setattr(fetch.time, "sleep", lambda _: None)
    monkeypatch.setattr(fetch.httpx, "get", lambda *args, **kwargs: _response(200, "ok"))

    result = fetch.fetch_episode_page.fn(16615, attempts=0)

    url = "https://www.hoerspiele.de/hsp_anzeige.asp?code=16615"
    expected_path = tmp_path / build_file_name(url)
    assert result == {
        "episode_code": 16615,
        "attempts": 0,
        "status": "success",
        "html_path": str(expected_path),
    }
    assert expected_path.read_text(encoding="utf-8") == "ok"


def test_fetch_episode_page_returns_not_found(monkeypatch):
    monkeypatch.setattr(fetch.time, "sleep", lambda _: None)
    monkeypatch.setattr(fetch.httpx, "get", lambda *args, **kwargs: _response(404))

    result = fetch.fetch_episode_page.fn(16615, attempts=2)

    assert result == {
        "episode_code": 16615,
        "attempts": 2,
        "status": "not_found",
        "html_path": None,
    }


def test_fetch_episode_page_raises_for_server_error(monkeypatch):
    monkeypatch.setattr(fetch.time, "sleep", lambda _: None)
    monkeypatch.setattr(fetch.httpx, "get", lambda *args, **kwargs: _response(500))

    with pytest.raises(RuntimeError, match="Server error 500"):
        fetch.fetch_episode_page.fn(16615, attempts=0)
