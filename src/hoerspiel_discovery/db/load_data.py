from __future__ import annotations

import json
import os
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client, Client

from hoerspiel_discovery.config import INTERIM_DATA_DIR

load_dotenv()


def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def load_records() -> list[dict]:
    path = INTERIM_DATA_DIR / "cleaned_details.json"
    return json.loads(path.read_text(encoding="utf-8"))


def parse_date(value: str | None) -> str | None:
    """Convert DD.MM.YYYY to YYYY-MM-DD for Postgres."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d.%m.%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def fetch_all(client: Client, table: str, columns: str) -> list[dict]:
    """Fetch all rows from a table, handling Supabase's 1000-row limit."""
    all_rows = []
    offset = 0
    PAGE_SIZE = 1000
    while True:
        result = (
            client.table(table)
            .select(columns)
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        all_rows.extend(result.data)
        if len(result.data) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return all_rows


def upsert_series(client: Client, records: list[dict]) -> dict[str, int]:
    """Insert all unique series, return name → id mapping."""
    seen = {}
    for r in records:
        name = r.get("series_name")
        label = r.get("label")
        if name and name not in seen:
            seen[name] = label

    rows = [{"name": name, "label": label} for name, label in seen.items()]
    client.table("series").upsert(rows, on_conflict="name").execute()

    all_series = fetch_all(client, "series", "id, name")
    return {s["name"]: s["id"] for s in all_series}


def upsert_genres(client: Client, records: list[dict]) -> dict[str, int]:
    """Insert all unique genres, return name → id mapping."""
    all_genres = set()
    for r in records:
        for g in (r.get("genres") or []):
            if g:
                all_genres.add(g)

    rows = [{"name": g} for g in sorted(all_genres)]
    client.table("genres").upsert(rows, on_conflict="name").execute()

    all_genres_db = fetch_all(client, "genres", "id, name")
    return {g["name"]: g["id"] for g in all_genres_db}


def upsert_speakers(client: Client, records: list[dict]) -> dict[str, int]:
    """Insert all unique speakers, return name → id mapping."""
    all_speakers = set()
    for r in records:
        for s in (r.get("speakers") or []):
            name = s.get("speaker")
            if name:
                all_speakers.add(name)

    rows = [{"name": s} for s in sorted(all_speakers)]

    # Insert in batches to avoid request size limits
    BATCH_SIZE = 500
    for i in range(0, len(rows), BATCH_SIZE):
        client.table("speakers").upsert(
            rows[i:i + BATCH_SIZE], on_conflict="name"
        ).execute()

    all_speakers_db = fetch_all(client, "speakers", "id, name")
    return {s["name"]: s["id"] for s in all_speakers_db}


def upsert_roles(client: Client, records: list[dict]) -> dict[str, int]:
    """Insert all unique roles, return name → id mapping."""
    all_roles = set()
    for r in records:
        for s in (r.get("speakers") or []):
            role = s.get("role")
            if role:
                all_roles.add(role)

    rows = [{"name": r} for r in sorted(all_roles)]

    BATCH_SIZE = 500
    for i in range(0, len(rows), BATCH_SIZE):
        client.table("roles").upsert(
            rows[i:i + BATCH_SIZE], on_conflict="name"
        ).execute()

    all_roles_db = fetch_all(client, "roles", "id, name")
    return {r["name"]: r["id"] for r in all_roles_db}


def load_episodes(
    client: Client,
    records: list[dict],
    series_map: dict[str, int],
    genre_map: dict[str, int],
    speaker_map: dict[str, int],
    role_map: dict[str, int],
) -> None:
    """Insert episodes and their junction table entries in batches."""
    BATCH_SIZE = 100

    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]
        print(f"  Episodes {i + 1}–{min(i + BATCH_SIZE, len(records))} / {len(records)}")

        # 1. Upsert episodes — deduplicate within batch by source_url
        seen_in_batch: set[str] = set()
        episode_rows = []
        for r in batch:
            source_url = r.get("source_url")
            if source_url and source_url in seen_in_batch:
                continue
            if source_url:
                seen_in_batch.add(source_url)
            series_id = series_map.get(r.get("series_name"))
            episode_rows.append({
                "series_id":        series_id,
                "episode_number":   r.get("episode_number"),
                "title":            r.get("title"),
                "description":      r.get("description"),
                "duration_minutes": r.get("duration_minutes"),
                "release_date":     parse_date(r.get("release_date")),
                "cover_url":        r.get("cover_url"),
                "order_number":     r.get("order_number"),
                "source_url":       source_url,
            })

        client.table("episodes").upsert(
            episode_rows, on_conflict="source_url"
        ).execute()

        # Build source_url → episode id map for this batch
        source_urls = [r.get("source_url") for r in batch if r.get("source_url")]
        if not source_urls:
            continue

        ep_result = client.table("episodes").select("id, source_url").in_(
            "source_url", source_urls
        ).execute()
        ep_map = {e["source_url"]: e["id"] for e in ep_result.data}

        # 2. Episode genres — deduplicate
        genre_rows = []
        seen_genre_pairs: set[tuple] = set()
        for r in batch:
            ep_id = ep_map.get(r.get("source_url"))
            if not ep_id:
                continue
            for g in (r.get("genres") or []):
                g_id = genre_map.get(g)
                if g_id:
                    pair = (ep_id, g_id)
                    if pair not in seen_genre_pairs:
                        seen_genre_pairs.add(pair)
                        genre_rows.append({"episode_id": ep_id, "genre_id": g_id})

        if genre_rows:
            client.table("episode_genres").upsert(
                genre_rows, on_conflict="episode_id,genre_id"
            ).execute()

        # 3. Episode speakers — deduplicate
        speaker_rows = []
        seen_speaker_triples: set[tuple] = set()
        for r in batch:
            ep_id = ep_map.get(r.get("source_url"))
            if not ep_id:
                continue
            for s in (r.get("speakers") or []):
                sp_id = speaker_map.get(s.get("speaker"))
                ro_id = role_map.get(s.get("role"))
                if sp_id and ro_id:
                    triple = (ep_id, sp_id, ro_id)
                    if triple not in seen_speaker_triples:
                        seen_speaker_triples.add(triple)
                        speaker_rows.append({
                            "episode_id": ep_id,
                            "speaker_id": sp_id,
                            "role_id":    ro_id,
                        })

        if speaker_rows:
            client.table("episode_speakers").upsert(
                speaker_rows,
                on_conflict="episode_id,speaker_id,role_id"
            ).execute()


def main() -> None:
    print("Connecting to Supabase...")
    client = get_client()

    print("Loading records...")
    records = load_records()
    print(f"  {len(records)} records loaded")

    # Deduplicate stub records (no source_url) by title + series + episode_number
    seen_stubs: set[tuple] = set()
    deduped_records = []
    for r in records:
        if r.get("source_url"):
            deduped_records.append(r)
        else:
            key = (r.get("series_name"), r.get("episode_number"), r.get("title"))
            if key not in seen_stubs:
                seen_stubs.add(key)
                deduped_records.append(r)

    print(f"  After deduplication: {len(deduped_records)} records")
    records = deduped_records

    print("\nUpserting series...")
    series_map = upsert_series(client, records)
    print(f"  {len(series_map)} series")

    print("\nUpserting genres...")
    genre_map = upsert_genres(client, records)
    print(f"  {len(genre_map)} genres")

    print("\nUpserting speakers...")
    speaker_map = upsert_speakers(client, records)
    print(f"  {len(speaker_map)} speakers")

    print("\nUpserting roles...")
    role_map = upsert_roles(client, records)
    print(f"  {len(role_map)} roles")

    print("\nLoading episodes...")
    load_episodes(client, records, series_map, genre_map, speaker_map, role_map)

    print("\nDone!")


if __name__ == "__main__":
    main()