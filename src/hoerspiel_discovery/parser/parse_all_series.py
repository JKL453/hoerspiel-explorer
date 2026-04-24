from __future__ import annotations

import json
from pathlib import Path

from bs4 import BeautifulSoup
from hoerspiel_discovery.config import (
    RAW_SERIES_PAGES_DIR,
    RAW_DETAIL_PAGES_DIR,
    INTERIM_DATA_DIR,
)
from hoerspiel_discovery.scraper.fetch_series import extract_episode_links, build_file_name
from hoerspiel_discovery.parser.parse_detail import load_html, parse_detail_page
from hoerspiel_discovery.cleaner.clean_detail import clean_detail_record


def extract_series_id_from_html(html: str) -> int | None:
    """Extract series ID from the series page HTML."""
    soup = BeautifulSoup(html, "lxml")
    link = soup.find("a", href=lambda h: h and "hsp_serie.asp?serie=" in h)
    if not link:
        return None
    href = link["href"]
    try:
        return int(href.split("serie=")[1].split("&")[0])
    except (IndexError, ValueError):
        return None


def main() -> None:
    INTERIM_DATA_DIR.mkdir(parents=True, exist_ok=True)

    series_files = sorted(RAW_SERIES_PAGES_DIR.glob("*.html"))
    print(f"Found {len(series_files)} series pages")

    all_records = []
    stats = {"with_detail": 0, "stub": 0, "missing_html": 0}

    for i, series_path in enumerate(series_files, start=1):
        html = load_html(series_path)
        base_url = "https://www.hoerspiele.de/"
        episodes = extract_episode_links(html, base_url)

        if not episodes:
            continue

        print(f"[{i}/{len(series_files)}] {series_path.name}: {len(episodes)} episodes")

        for ep in episodes:
            if not ep["has_detail_page"]:
                # Stub record — no detail page available
                record = {
                    "title":            ep["title"],
                    "series_name":      ep["series_name"],
                    "episode_number":   ep["episode_number"],
                    "source_url":       None,
                    "description":      None,
                    "duration_minutes": None,
                    "release_date":     None,
                    "label":            None,
                    "cover_url":        None,
                    "speakers":         [],
                    "order_number":     None,
                    "genres":           [],
                    "previous_episode_url": None,
                    "next_episode_url":     None,
                }
                all_records.append(record)
                stats["stub"] += 1
                continue

            # Check if detail HTML exists locally
            file_name = build_file_name(ep["url"])
            detail_path = RAW_DETAIL_PAGES_DIR / file_name

            if not detail_path.exists():
                # Detail page not scraped yet — stub with URL
                record = {
                    "title":            ep["title"],
                    "series_name":      ep["series_name"],
                    "episode_number":   ep["episode_number"],
                    "source_url":       ep["url"],
                    "description":      None,
                    "duration_minutes": None,
                    "release_date":     None,
                    "label":            None,
                    "cover_url":        None,
                    "speakers":         [],
                    "order_number":     None,
                    "genres":           [],
                    "previous_episode_url": None,
                    "next_episode_url":     None,
                }
                all_records.append(record)
                stats["missing_html"] += 1
                continue

            # Parse + clean existing detail HTML
            try:
                detail_html = load_html(detail_path)
                parsed = parse_detail_page(detail_html)
                parsed["source_url"] = ep["url"]
                cleaned = clean_detail_record(parsed)
                all_records.append(cleaned)
                stats["with_detail"] += 1
            except Exception as e:
                print(f"  ERROR parsing {detail_path.name}: {e}")

    # Deduplicate by source_url — keep first occurrence
    seen_urls: set[str] = set()
    deduped = []
    for r in all_records:
        url = r.get("source_url")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        deduped.append(r)

    output_path = INTERIM_DATA_DIR / "cleaned_details.json"
    output_path.write_text(
        json.dumps(deduped, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n=== Done ===")
    print(f"With detail page:  {stats['with_detail']}")
    print(f"Stub (no link):    {stats['stub']}")
    print(f"Stub (not scraped): {stats['missing_html']}")
    print(f"Total records:     {len(deduped)}")
    print(f"Saved to:          {output_path}")


if __name__ == "__main__":
    main()