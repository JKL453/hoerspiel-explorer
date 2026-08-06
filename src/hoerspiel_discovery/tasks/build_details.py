from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from prefect import task

from hoerspiel_discovery.cleaner.clean_detail import clean_detail_record
from hoerspiel_discovery.config import (
    INTERIM_DATA_DIR,
    RAW_DETAIL_PAGES_DIR,
    RAW_SERIES_PAGES_DIR,
)
from hoerspiel_discovery.parser.parse_all_series import (
    apply_role_normalization,
    apply_speaker_normalization,
    build_role_normalization_map,
    build_speaker_normalization_map,
    normalize_series_name,
)
from hoerspiel_discovery.parser.parse_detail import load_html, parse_detail_page
from hoerspiel_discovery.scraper.fetch_series import (
    build_file_name,
    extract_episode_links,
)

BASE_URL = "https://www.hoerspiele.de/"
RECORD_KEYS = {
    "title",
    "series_name",
    "episode_number",
    "description",
    "duration_minutes",
    "release_date",
    "label",
    "cover_url",
    "speakers",
    "order_number",
    "genres",
    "previous_episode_url",
    "next_episode_url",
    "source_url",
}


def _write_json_atomically(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    temporary_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(path)


def _build_stub(episode: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": episode["title"],
        "series_name": normalize_series_name(episode["series_name"]),
        "episode_number": episode["episode_number"],
        "source_url": episode["url"],
        "description": None,
        "duration_minutes": None,
        "release_date": None,
        "label": None,
        "cover_url": None,
        "speakers": [],
        "order_number": None,
        "genres": [],
        "previous_episode_url": None,
        "next_episode_url": None,
    }


def _parse_episode(
    episode: dict[str, Any],
    detail_pages_dir: Path,
) -> tuple[dict[str, Any], str, str | None]:
    if not episode["has_detail_page"]:
        return _build_stub(episode), "stub_without_link", None

    detail_path = detail_pages_dir / build_file_name(episode["url"])
    if not detail_path.exists():
        return _build_stub(episode), "stub_missing_html", None

    try:
        parsed = parse_detail_page(load_html(detail_path))
        parsed["source_url"] = episode["url"]
        cleaned = clean_detail_record(parsed)
        if not cleaned["title"] or not cleaned["series_name"]:
            raise ValueError("parsed detail page has no title or series name")
        return cleaned, "with_detail", None
    except Exception as exc:
        error = f"{detail_path}: {type(exc).__name__}: {exc}"
        return _build_stub(episode), "stub_parse_error", error


def _deduplicate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_urls: set[str] = set()
    seen_stubs: set[tuple[Any, Any, Any]] = set()
    deduplicated = []

    for record in records:
        source_url = record.get("source_url")
        if source_url:
            if source_url in seen_urls:
                continue
            seen_urls.add(source_url)
        else:
            key = (
                record.get("series_name"),
                record.get("episode_number"),
                record.get("title"),
            )
            if key in seen_stubs:
                continue
            seen_stubs.add(key)
        deduplicated.append(record)

    return deduplicated


def _is_stub(record: dict[str, Any]) -> bool:
    return (
        record.get("description") is None
        and record.get("duration_minutes") is None
        and record.get("release_date") is None
        and record.get("label") is None
        and record.get("cover_url") is None
        and not record.get("speakers")
        and not record.get("genres")
    )


def _validate_records(records: list[dict[str, Any]]) -> dict[str, int]:
    if not records:
        raise ValueError("candidate contains no records")

    seen_urls: set[str] = set()
    speakers: set[str] = set()
    roles: set[str] = set()
    genres: set[str] = set()
    stubs = 0

    for index, record in enumerate(records):
        missing_keys = RECORD_KEYS - record.keys()
        if missing_keys:
            raise ValueError(
                f"record {index} is missing keys: {sorted(missing_keys)}"
            )
        if not isinstance(record["speakers"], list):
            raise ValueError(f"record {index} has non-list speakers")
        if not isinstance(record["genres"], list):
            raise ValueError(f"record {index} has non-list genres")

        source_url = record["source_url"]
        if source_url:
            if source_url in seen_urls:
                raise ValueError(f"duplicate source_url: {source_url}")
            seen_urls.add(source_url)

        if _is_stub(record):
            stubs += 1
        genres.update(record["genres"])
        for speaker_entry in record["speakers"]:
            if speaker_entry.get("speaker"):
                speakers.add(speaker_entry["speaker"])
            if speaker_entry.get("role"):
                roles.add(speaker_entry["role"])

    return {
        "records": len(records),
        "stubs": stubs,
        "speakers": len(speakers),
        "roles": len(roles),
        "genres": len(genres),
    }


@task(log_prints=True)
def parse_and_clean_details() -> dict[str, Any]:
    """Parse all series and detail pages and write a cleaned staging artifact."""
    series_files = sorted(RAW_SERIES_PAGES_DIR.glob("*.html"))
    if not series_files:
        raise FileNotFoundError(f"No series pages found in {RAW_SERIES_PAGES_DIR}")

    print(f"Found {len(series_files)} series pages in {RAW_SERIES_PAGES_DIR}.")
    records: list[dict[str, Any]] = []
    stats = {
        "series_pages": len(series_files),
        "with_detail": 0,
        "stub_without_link": 0,
        "stub_missing_html": 0,
        "stub_parse_error": 0,
        "parse_errors": [],
    }

    for index, series_path in enumerate(series_files, start=1):
        episodes = extract_episode_links(load_html(series_path), BASE_URL)
        for episode in episodes:
            record, outcome, error = _parse_episode(
                episode,
                RAW_DETAIL_PAGES_DIR,
            )
            records.append(record)
            stats[outcome] += 1
            if error:
                stats["parse_errors"].append(error)
                print(f"Parse error converted to stub: {error}")

        if index % 100 == 0 or index == len(series_files):
            print(
                f"Progress: {index}/{len(series_files)} series, "
                f"{len(records)} records "
                f"(detail={stats['with_detail']}, "
                f"no_link={stats['stub_without_link']}, "
                f"missing_html={stats['stub_missing_html']}, "
                f"parse_error={stats['stub_parse_error']})."
            )

    staging_path = INTERIM_DATA_DIR / "cleaned_details_staging.json"
    _write_json_atomically(staging_path, records)
    print(f"Saved {len(records)} records to staging artifact {staging_path}.")
    return {"path": str(staging_path), "stats": stats}


@task(log_prints=True)
def normalize_details(staging_result: dict[str, Any]) -> dict[str, Any]:
    """Deduplicate and globally normalize staged records."""
    staging_path = Path(staging_result["path"])
    records = json.loads(staging_path.read_text(encoding="utf-8"))
    deduplicated = _deduplicate(records)
    print(f"Deduplicated {len(records)} staged records to {len(deduplicated)}.")

    speaker_map = build_speaker_normalization_map(deduplicated)
    apply_speaker_normalization(deduplicated, speaker_map)
    role_map = build_role_normalization_map(deduplicated)
    apply_role_normalization(deduplicated, role_map)

    candidate_path = INTERIM_DATA_DIR / "cleaned_details_candidate.json"
    _write_json_atomically(candidate_path, deduplicated)
    print(
        f"Saved normalized candidate to {candidate_path} "
        f"({len(speaker_map)} speaker and {len(role_map)} role mappings)."
    )
    return {
        "path": str(candidate_path),
        "parse_stats": staging_result["stats"],
        "normalization": {
            "speaker_mappings": len(speaker_map),
            "role_mappings": len(role_map),
        },
    }


@task(log_prints=True)
def validate_and_publish_details(candidate_result: dict[str, Any]) -> dict[str, Any]:
    """Validate the candidate and atomically publish cleaned_details.json."""
    candidate_path = Path(candidate_result["path"])
    records = json.loads(candidate_path.read_text(encoding="utf-8"))
    validation_stats = _validate_records(records)

    output_path = INTERIM_DATA_DIR / "cleaned_details.json"
    candidate_path.replace(output_path)
    print(f"Published validated artifact to {output_path}.")
    print(
        "Final statistics: "
        f"records={validation_stats['records']}, "
        f"stubs={validation_stats['stubs']}, "
        f"speakers={validation_stats['speakers']}, "
        f"roles={validation_stats['roles']}, "
        f"genres={validation_stats['genres']}."
    )
    return {
        "path": str(output_path),
        "validation": validation_stats,
        "parse_stats": candidate_result["parse_stats"],
        "normalization": candidate_result["normalization"],
    }
