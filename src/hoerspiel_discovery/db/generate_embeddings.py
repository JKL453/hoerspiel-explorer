from __future__ import annotations

import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client, Client

load_dotenv()


def get_openai_client() -> OpenAI:
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def get_supabase_client() -> Client:
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_KEY"],
    )


def build_embedding_text(episode: dict) -> str:
    parts = []

    if episode.get("title"):
        parts.append(f"Titel: {episode['title']}")

    if episode.get("series_name"):
        parts.append(f"Serie: {episode['series_name']}")

    if episode.get("description"):
        parts.append(f"Beschreibung: {episode['description']}")

    if episode.get("genres"):
        parts.append(f"Genre: {', '.join(episode['genres'])}")

    if episode.get("speakers"):
        speaker_names = sorted({s["speaker"] for s in episode["speakers"]})
        parts.append(f"Sprecher: {', '.join(speaker_names)}")

    return " | ".join(parts)


def fetch_episodes_without_embeddings(supabase: Client) -> list[dict]:
    """Fetch all episodes that have a description but no embedding yet."""
    all_episodes = []
    offset = 0
    PAGE_SIZE = 1000

    while True:
        result = (
            supabase.table("episodes")
            .select("id, title, description, series_id")
            .is_("embedding", "null")
            .not_.is_("description", "null")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        all_episodes.extend(result.data)
        if len(result.data) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    return all_episodes


def fetch_series_map(supabase: Client) -> dict[int, str]:
    """Fetch series id → name mapping."""
    all_series = []
    offset = 0
    PAGE_SIZE = 1000
    while True:
        result = (
            supabase.table("series")
            .select("id, name")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        all_series.extend(result.data)
        if len(result.data) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return {s["id"]: s["name"] for s in all_series}


def fetch_genre_map(supabase: Client) -> dict[int, list[str]]:
    """Fetch episode_id → list of genre names."""
    all_rows = []
    offset = 0
    PAGE_SIZE = 1000
    while True:
        result = (
            supabase.table("episode_genres")
            .select("episode_id, genres(name)")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        all_rows.extend(result.data)
        if len(result.data) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    genre_map: dict[int, list[str]] = {}
    for row in all_rows:
        ep_id = row["episode_id"]
        genre_name = row["genres"]["name"]
        genre_map.setdefault(ep_id, []).append(genre_name)
    return genre_map


def fetch_speaker_map(supabase: Client) -> dict[int, list[dict]]:
    """Fetch episode_id → list of speaker/role dicts."""
    all_rows = []
    offset = 0
    PAGE_SIZE = 1000
    while True:
        result = (
            supabase.table("episode_speakers")
            .select("episode_id, speakers(name), roles(name)")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        all_rows.extend(result.data)
        if len(result.data) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    speaker_map: dict[int, list[dict]] = {}
    for row in all_rows:
        ep_id = row["episode_id"]
        speaker_map.setdefault(ep_id, []).append({
            "speaker": row["speakers"]["name"],
            "role":    row["roles"]["name"],
        })
    return speaker_map


def generate_embeddings(
    openai: OpenAI,
    texts: list[str],
    model: str = "text-embedding-3-small",
) -> list[list[float]]:
    """Generate embeddings for a batch of texts."""
    response = openai.embeddings.create(input=texts, model=model)
    return [item.embedding for item in response.data]


def main() -> None:
    print("Connecting...")
    openai = get_openai_client()
    supabase = get_supabase_client()

    print("Fetching episodes without embeddings...")
    episodes = fetch_episodes_without_embeddings(supabase)
    print(f"  {len(episodes)} episodes to embed")

    if not episodes:
        print("Nothing to do!")
        return

    print("Fetching series, genre and speaker maps...")
    series_map = fetch_series_map(supabase)
    genre_map = fetch_genre_map(supabase)
    speaker_map = fetch_speaker_map(supabase)

    for ep in episodes:
        ep["series_name"] = series_map.get(ep["series_id"])
        ep["genres"]      = genre_map.get(ep["id"], [])
        ep["speakers"]    = speaker_map.get(ep["id"], [])
        
    BATCH_SIZE = 100
    total = len(episodes)
    embedded = 0

    for i in range(0, total, BATCH_SIZE):
        batch = episodes[i:i + BATCH_SIZE]
        texts = [build_embedding_text(ep) for ep in batch]

        print(f"  Embedding {i + 1}–{min(i + BATCH_SIZE, total)} / {total}")

        try:
            embeddings = generate_embeddings(openai, texts)
        except Exception as e:
            print(f"  ERROR generating embeddings: {e}")
            time.sleep(5)
            continue

        # Write embeddings back to Supabase
        for ep, embedding in zip(batch, embeddings):
            try:
                supabase.table("episodes").update(
                    {"embedding": embedding}
                ).eq("id", ep["id"]).execute()
                embedded += 1
            except Exception as e:
                print(f"  ERROR saving embedding for episode {ep['id']}: {e}")

        # Be nice to the API
        time.sleep(0.1)

    print(f"\nDone! {embedded} embeddings generated.")


if __name__ == "__main__":
    main()