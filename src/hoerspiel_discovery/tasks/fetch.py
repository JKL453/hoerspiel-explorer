from pathlib import Path
import time

from prefect import task
import httpx

from hoerspiel_discovery.scraper.fetch_series import build_file_name

SERIES_PAGES_DIR = Path("/data/hoerspiel-explorer/raw/series_pages")
DETAIL_PAGES_DIR = Path("/data/hoerspiel-explorer/raw/detail_pages")


@task(retries=3, retry_delay_seconds=[10, 30], log_prints=True)
def fetch_series_page(external_id: int) -> dict:
    """
    Fetches a single series page by ID and stores the raw HTML on disk.
    Distinguishes between 'not found' (expected, no retry needed)
    and transient errors (retried automatically by Prefect).
    """
    url = f"https://www.hoerspiele.de/hsp_serie.asp?serie={external_id}"

    try:
        response = httpx.get(url, timeout=15.0)
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        raise RuntimeError(f"Transient error for ID {external_id}: {e}")

    if response.status_code == 404:
        return {"external_id": external_id, "status": "not_found", "html_path": None}

    if response.status_code >= 500:
        raise RuntimeError(f"Server error {response.status_code} for ID {external_id}")

    response.raise_for_status()

    SERIES_PAGES_DIR.mkdir(parents=True, exist_ok=True)
    path = SERIES_PAGES_DIR / f"{external_id}.html"
    path.write_text(response.text, encoding="utf-8")

    return {"external_id": external_id, "status": "success", "html_path": str(path)}


@task(retries=3, retry_delay_seconds=[10, 30], log_prints=True)
def fetch_episode_page(episode_code: int, attempts: int) -> dict:
    """Fetches one episode detail page and stores it under its legacy filename."""
    url = f"https://www.hoerspiele.de/hsp_anzeige.asp?code={episode_code}"

    # Keep request frequency low for the source website.
    time.sleep(3.0)

    try:
        response = httpx.get(url, timeout=15.0)
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        raise RuntimeError(f"Transient error for episode {episode_code}: {e}")

    if response.status_code == 404:
        return {
            "episode_code": episode_code,
            "attempts": attempts,
            "status": "not_found",
            "html_path": None,
        }

    if response.status_code >= 500:
        raise RuntimeError(
            f"Server error {response.status_code} for episode {episode_code}"
        )

    response.raise_for_status()

    DETAIL_PAGES_DIR.mkdir(parents=True, exist_ok=True)
    path = DETAIL_PAGES_DIR / build_file_name(url)
    path.write_text(response.text, encoding="utf-8")

    return {
        "episode_code": episode_code,
        "attempts": attempts,
        "status": "success",
        "html_path": str(path),
    }
