from __future__ import annotations

import json
import time
import logging
from pathlib import Path

import requests

from hoerspiel_discovery.config import INTERIM_DATA_DIR

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "hoerspiel-explorer/0.1 (learning project; respectful crawling)"
}

# Polite delay between MusicBrainz requests (they ask for max 1 req/sec)
DELAY = 1.1


def search_release(series_name: str, title: str, episode_number: int | None) -> str | None:
    """Search MusicBrainz for a release and return the best matching release ID."""
    # Build query: prefer episode number + title for precision
    if episode_number:
        query = f"{series_name} {episode_number} {title}"
    else:
        query = f"{series_name} {title}"

    url = "https://musicbrainz.org/ws/2/release"
    params = {
        "query": query,
        "fmt": "json",
        "limit": 5,
    }

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning(f"MusicBrainz search failed for '{query}': {e}")
        return None

    releases = data.get("releases", [])
    if not releases:
        return None

    # Take highest scoring release
    best = max(releases, key=lambda r: r.get("score", 0))
    if best.get("score", 0) < 80:
        return None

    return best["id"]


def get_cover_url(release_id: str) -> str | None:
    """Fetch cover art URL from Cover Art Archive."""
    url = f"https://coverartarchive.org/release/{release_id}/front"

    try:
        r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        if r.status_code == 200:
            return r.url
        return None
    except Exception as e:
        logger.warning(f"Cover Art Archive failed for {release_id}: {e}")
        return None


def enrich_covers(records: list[dict]) -> tuple[list[dict], dict]:
    """
    Enrich records without cover_url using MusicBrainz.
    Returns updated records and stats.
    """
    stats = {"checked": 0, "found": 0, "not_found": 0, "skipped": 0}

    for i, record in enumerate(records):
        # Skip if already has cover
        if record.get("cover_url"):
            stats["skipped"] += 1
            continue

        # Skip stubs with no title
        if not record.get("title") or not record.get("series_name"):
            stats["skipped"] += 1
            continue

        stats["checked"] += 1
        logger.info(
            f"[{i+1}/{len(records)}] Searching cover for: "
            f"{record['series_name']} - {record['title']}"
        )

        # Search MusicBrainz
        time.sleep(DELAY)
        release_id = search_release(
            series_name=record["series_name"],
            title=record["title"],
            episode_number=record.get("episode_number"),
        )

        if not release_id:
            stats["not_found"] += 1
            continue

        # Get cover URL
        time.sleep(DELAY)
        cover_url = get_cover_url(release_id)

        if cover_url:
            record["cover_url"] = cover_url
            stats["found"] += 1
            logger.info(f"  ✓ Found cover: {cover_url}")
        else:
            stats["not_found"] += 1

    return records, stats


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    input_path = INTERIM_DATA_DIR / "cleaned_details.json"
    output_path = INTERIM_DATA_DIR / "cleaned_details.json"

    print(f"Loading records from {input_path}...")
    records = json.loads(input_path.read_text(encoding="utf-8"))

    no_cover = sum(1 for r in records if not r.get("cover_url"))
    print(f"Records without cover: {no_cover} / {len(records)}")

    print("\nStarting MusicBrainz cover enrichment...")
    records, stats = enrich_covers(records)

    print(f"\n=== Done ===")
    print(f"Checked:    {stats['checked']}")
    print(f"Found:      {stats['found']}")
    print(f"Not found:  {stats['not_found']}")
    print(f"Skipped:    {stats['skipped']} (already had cover)")

    print(f"\nSaving to {output_path}...")
    output_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("Done!")


if __name__ == "__main__":
    main()