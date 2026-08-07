from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from prefect import task
from supabase import Client

from hoerspiel_discovery.config import INTERIM_DATA_DIR
from hoerspiel_discovery.db.load_data import fetch_all, get_client
from hoerspiel_discovery.tasks.build_details import _validate_records

DIMENSION_BATCH_SIZE = 500
EPISODE_BATCH_SIZE = 100
PRODUCT_TABLES = (
    "episode_speakers",
    "episode_genres",
    "episodes",
    "speakers",
    "roles",
    "genres",
    "series",
)


def _batches(rows: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def _parse_date_strict(value: str | None) -> str | None:
    if value is None:
        return None
    return datetime.strptime(value, "%d.%m.%Y").strftime("%Y-%m-%d")


def _collect_dimensions(records: list[dict[str, Any]]) -> dict[str, list[dict]]:
    series_labels: dict[str, str | None] = {}
    genres: set[str] = set()
    speakers: set[str] = set()
    roles: set[str] = set()

    for record in records:
        series_name = record["series_name"]
        label = record.get("label")
        if series_name not in series_labels or (
            series_labels[series_name] is None and label is not None
        ):
            series_labels[series_name] = label
        genres.update(record["genres"])
        for entry in record["speakers"]:
            speakers.add(entry["speaker"])
            roles.add(entry["role"])

    return {
        "series": [
            {"name": name, "label": label}
            for name, label in sorted(series_labels.items())
        ],
        "genres": [{"name": name} for name in sorted(genres)],
        "speakers": [{"name": name} for name in sorted(speakers)],
        "roles": [{"name": name} for name in sorted(roles)],
    }


def _build_manifest(records: list[dict[str, Any]]) -> dict[str, int]:
    validation = _validate_records(records)
    invalid_dates = []
    episode_genres: set[tuple[str, str]] = set()
    episode_speakers: set[tuple[str, str, str]] = set()

    for index, record in enumerate(records):
        if not record.get("title") or not record.get("series_name"):
            raise ValueError(f"record {index} has no title or series_name")
        try:
            _parse_date_strict(record.get("release_date"))
        except ValueError:
            invalid_dates.append((index, record.get("release_date")))

        for genre in record["genres"]:
            episode_genres.add((record["source_key"], genre))
        for entry in record["speakers"]:
            if not entry.get("speaker") or not entry.get("role"):
                raise ValueError(f"record {index} has an invalid speaker entry")
            episode_speakers.add(
                (record["source_key"], entry["speaker"], entry["role"])
            )

    if invalid_dates:
        preview = ", ".join(f"#{i}={value!r}" for i, value in invalid_dates[:5])
        raise ValueError(f"invalid release dates ({len(invalid_dates)}): {preview}")

    dimensions = _collect_dimensions(records)
    return {
        "series": len(dimensions["series"]),
        "episodes": validation["records"],
        "speakers": len(dimensions["speakers"]),
        "roles": len(dimensions["roles"]),
        "genres": len(dimensions["genres"]),
        "episode_speakers": len(episode_speakers),
        "episode_genres": len(episode_genres),
        "stubs": validation["stubs"],
    }


def _table_count(client: Client, table: str) -> int:
    response = client.table(table).select("*", count="exact").limit(1).execute()
    if response.count is None:
        raise RuntimeError(f"Supabase returned no exact count for {table}")
    return response.count


def _read_records(path: str) -> list[dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _upsert_named_rows(
    client: Client,
    table: str,
    rows: list[dict[str, Any]],
) -> None:
    for index, batch in enumerate(_batches(rows, DIMENSION_BATCH_SIZE), start=1):
        client.table(table).upsert(batch, on_conflict="name").execute()
        print(f"{table}: loaded batch {index} ({len(batch)} rows).")


@task(log_prints=True)
def preflight_cleaned_details() -> dict[str, Any]:
    path = INTERIM_DATA_DIR / "cleaned_details.json"
    if not path.exists():
        raise FileNotFoundError(f"Cleaned artifact not found: {path}")
    records = _read_records(str(path))
    manifest = _build_manifest(records)
    print(f"Preflight passed for {manifest['episodes']} episodes at {path}.")
    print(f"Expected database counts: {manifest}")
    return {"path": str(path), "manifest": manifest}


@task(log_prints=True)
def assert_empty_destination(preflight: dict[str, Any]) -> dict[str, Any]:
    client = get_client()
    counts = {table: _table_count(client, table) for table in PRODUCT_TABLES}
    nonempty = {table: count for table, count in counts.items() if count}
    if nonempty:
        raise RuntimeError(
            "Initial load refused because product tables are not empty: "
            f"{nonempty}. Run the reviewed manual TRUNCATE first."
        )
    print("Destination safety check passed: all product tables are empty.")
    return preflight


@task(log_prints=True)
def load_dimensions(preflight: dict[str, Any]) -> dict[str, Any]:
    records = _read_records(preflight["path"])
    dimensions = _collect_dimensions(records)
    client = get_client()
    for table in ("series", "genres", "speakers", "roles"):
        _upsert_named_rows(client, table, dimensions[table])
    print("All dimensions loaded.")
    return preflight


@task(log_prints=True)
def load_episodes_and_relationships(preflight: dict[str, Any]) -> dict[str, Any]:
    records = _read_records(preflight["path"])
    client = get_client()
    series_map = {
        row["name"]: row["id"] for row in fetch_all(client, "series", "id, name")
    }
    genre_map = {
        row["name"]: row["id"] for row in fetch_all(client, "genres", "id, name")
    }
    speaker_map = {
        row["name"]: row["id"]
        for row in fetch_all(client, "speakers", "id, name")
    }
    role_map = {
        row["name"]: row["id"] for row in fetch_all(client, "roles", "id, name")
    }

    total = len(records)
    for batch_number, batch in enumerate(_batches(records, EPISODE_BATCH_SIZE), start=1):
        episode_rows = []
        for record in batch:
            series_id = series_map.get(record["series_name"])
            if series_id is None:
                raise RuntimeError(f"Missing series mapping: {record['series_name']}")
            episode_rows.append(
                {
                    "source_key": record["source_key"],
                    "source_url": record["source_url"],
                    "series_id": series_id,
                    "episode_number": record["episode_number"],
                    "title": record["title"],
                    "description": record["description"],
                    "duration_minutes": record["duration_minutes"],
                    "release_date": _parse_date_strict(record["release_date"]),
                    "cover_url": record["cover_url"],
                    "order_number": record["order_number"],
                }
            )

        client.table("episodes").upsert(
            episode_rows,
            on_conflict="source_key",
        ).execute()
        source_keys = [record["source_key"] for record in batch]
        response = (
            client.table("episodes")
            .select("id, source_key")
            .in_("source_key", source_keys)
            .execute()
        )
        episode_map = {row["source_key"]: row["id"] for row in response.data}
        if len(episode_map) != len(batch):
            raise RuntimeError(
                f"Could not resolve all episode IDs in batch {batch_number}"
            )

        genre_rows: list[dict[str, int]] = []
        speaker_rows: list[dict[str, int]] = []
        seen_genres: set[tuple[int, int]] = set()
        seen_speakers: set[tuple[int, int, int]] = set()
        for record in batch:
            episode_id = episode_map[record["source_key"]]
            for genre in record["genres"]:
                pair = (episode_id, genre_map[genre])
                if pair not in seen_genres:
                    seen_genres.add(pair)
                    genre_rows.append({"episode_id": pair[0], "genre_id": pair[1]})
            for entry in record["speakers"]:
                triple = (
                    episode_id,
                    speaker_map[entry["speaker"]],
                    role_map[entry["role"]],
                )
                if triple not in seen_speakers:
                    seen_speakers.add(triple)
                    speaker_rows.append(
                        {
                            "episode_id": triple[0],
                            "speaker_id": triple[1],
                            "role_id": triple[2],
                        }
                    )

        if genre_rows:
            client.table("episode_genres").upsert(
                genre_rows,
                on_conflict="episode_id,genre_id",
            ).execute()
        if speaker_rows:
            client.table("episode_speakers").upsert(
                speaker_rows,
                on_conflict="episode_id,speaker_id,role_id",
            ).execute()

        processed = min(batch_number * EPISODE_BATCH_SIZE, total)
        print(
            f"Episodes: {processed}/{total} loaded "
            f"(genres={len(genre_rows)}, speakers={len(speaker_rows)} in batch)."
        )

    return preflight


@task(log_prints=True)
def validate_loaded_database(preflight: dict[str, Any]) -> dict[str, Any]:
    client = get_client()
    expected = preflight["manifest"]
    actual = {table: _table_count(client, table) for table in PRODUCT_TABLES}
    mismatches = {
        table: {"expected": expected[table], "actual": actual[table]}
        for table in PRODUCT_TABLES
        if expected[table] != actual[table]
    }
    if mismatches:
        raise RuntimeError(f"Post-load count validation failed: {mismatches}")
    print(f"Post-load validation passed: {actual}")
    return {"manifest": expected, "actual": actual, "path": preflight["path"]}
