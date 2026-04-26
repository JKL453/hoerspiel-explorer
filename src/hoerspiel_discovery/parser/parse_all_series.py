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
    
def build_speaker_normalization_map(records: list[dict]) -> dict[str, str]:
    """
    Build a mapping from ascii-umlaut variants to the correct umlaut spelling.
    Only normalizes when the umlaut version appears more often.
    Respects SPEAKER_NAME_WHITELIST.
    """
    from collections import Counter
    from hoerspiel_discovery.cleaner.clean_detail import (
        SPEAKER_NAME_WHITELIST,
        _normalized_key,
        _normalize_umlaut,
    )

    # Count occurrences of each exact spelling
    counts: Counter[str] = Counter()
    for r in records:
        for s in (r.get("speakers") or []):
            name = s.get("speaker", "")
            if name:
                counts[name] += 1

    # Group by normalized key
    from collections import defaultdict
    groups: dict[str, list[str]] = defaultdict(list)
    for name in counts:
        groups[_normalized_key(name)].append(name)

    # Build map: variant → canonical (most common umlaut version wins)
    normalization_map: dict[str, str] = {}
    for norm_key, variants in groups.items():
        if len(variants) == 1:
            continue  # no conflict

        # Find the umlaut version (the one that changes when normalized)
        umlaut_variants = [v for v in variants if _normalize_umlaut(v) == v]
        ascii_variants  = [v for v in variants if _normalize_umlaut(v) != v]

        if not umlaut_variants or not ascii_variants:
            continue  # no clear ascii vs umlaut split

        # Pick most common umlaut version as canonical
        canonical = max(umlaut_variants, key=lambda v: counts[v])

        if canonical in SPEAKER_NAME_WHITELIST:
            continue

        for variant in ascii_variants:
            if variant != canonical:
                normalization_map[variant] = canonical
                print(f"  Normalize: '{variant}' → '{canonical}'")

    return normalization_map


def apply_speaker_normalization(
    records: list[dict],
    norm_map: dict[str, str],
) -> list[dict]:
    for r in records:
        for s in (r.get("speakers") or []):
            original = s.get("speaker", "")
            if original in norm_map:
                s["speaker"] = norm_map[original]
    return records

def build_role_normalization_map(records: list[dict]) -> dict[str, str]:
    """
    Build a mapping for role name variants.
    Most common spelling wins — handles capitalization and umlaut inconsistencies.
    """
    from collections import Counter, defaultdict
    from hoerspiel_discovery.cleaner.clean_detail import _normalized_key

    counts: Counter[str] = Counter()
    for r in records:
        for s in (r.get("speakers") or []):
            role = s.get("role", "")
            if role:
                counts[role] += 1

    groups: dict[str, list[str]] = defaultdict(list)
    for role in counts:
        groups[_normalized_key(role)].append(role)

    normalization_map: dict[str, str] = {}
    for norm_key, variants in groups.items():
        if len(variants) == 1:
            continue

        # Most common spelling wins
        canonical = max(variants, key=lambda v: counts[v])

        for variant in variants:
            if variant != canonical:
                normalization_map[variant] = canonical
                print(f"  Normalize role: '{variant}' → '{canonical}'")

    return normalization_map


def apply_role_normalization(
    records: list[dict],
    norm_map: dict[str, str],
) -> list[dict]:
    for r in records:
        for s in (r.get("speakers") or []):
            original = s.get("role", "")
            if original in norm_map:
                s["role"] = norm_map[original]
    return records

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

    # Normalize speaker names
    print("\nBuilding speaker normalization map...")
    norm_map = build_speaker_normalization_map(deduped)
    print(f"Normalizing {len(norm_map)} name variants")
    deduped = apply_speaker_normalization(deduped, norm_map)

    # Normalize role names
    print("\nBuilding role normalization map...")
    role_norm_map = build_role_normalization_map(deduped)
    print(f"Normalizing {len(role_norm_map)} role variants")
    deduped = apply_role_normalization(deduped, role_norm_map)

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