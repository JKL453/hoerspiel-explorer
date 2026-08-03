from pathlib import Path
from prefect import task
import httpx

SERIES_PAGES_DIR = Path("/data/hoerspiel-explorer/raw/series_pages")


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