import re
from pathlib import Path
from prefect import task

from hoerspiel_discovery.scraper.fetch_series import extract_episode_links
from hoerspiel_discovery.tasks.db_updates import supabase

BASE_URL = "https://www.hoerspiele.de/"


def _extract_code_from_url(url: str) -> int | None:
    match = re.search(r"code=(\d+)", url)
    return int(match.group(1)) if match else None


@task(log_prints=True)
def parse_series_page(external_id: int, html_path: str) -> int:
    html = Path(html_path).read_text(encoding="utf-8")
    episodes = extract_episode_links(html, base_url=BASE_URL)

    rows = [
        {
            "series_external_id": external_id,
            "episode_code": _extract_code_from_url(ep["url"]),
            "status": "pending",
        }
        for ep in episodes
        if ep["has_detail_page"]
    ]

    if rows:
        supabase.table("episode_targets").upsert(
            rows, on_conflict="episode_code"
        ).execute()

    print(f"Series {external_id}: {len(rows)} episode(s) with detail page found.")
    return len(rows)