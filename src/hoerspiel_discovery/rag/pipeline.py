from __future__ import annotations

import os
from dotenv import load_dotenv
import google.genai as genai
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


def get_gemini_client():
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    return client


def embed_query(openai: OpenAI, query: str) -> list[float]:
    """Embed a user query using the same model as the episodes."""
    response = openai.embeddings.create(
        input=query,
        model="text-embedding-3-small",
    )
    return response.data[0].embedding


def search_episodes(
    supabase: Client,
    query_embedding: list[float],
    match_count: int = 10,
    filter_genre: str | None = None,
) -> list[dict]:
    """Find the most similar episodes using pgvector."""
    result = supabase.rpc(
        "match_episodes",
        {
            "query_embedding": query_embedding,
            "match_count":     match_count,
            "filter_genre":    filter_genre,
        }
    ).execute()
    return result.data


def build_context(episodes: list[dict]) -> str:
    """Format retrieved episodes as context for the LLM."""
    lines = []
    for ep in episodes:
        parts = [f"**{ep['title']}**"]
        if ep.get("series_name"):
            parts.append(f"Serie: {ep['series_name']}")
        if ep.get("episode_number"):
            parts.append(f"Folge {ep['episode_number']}")
        if ep.get("release_date"):
            parts.append(f"({ep['release_date'][:4]})")
        if ep.get("description"):
            parts.append(f"\n{ep['description']}")
        lines.append(" | ".join(parts[:4]) + (f"\n{ep['description']}" if ep.get("description") else ""))
    return "\n\n".join(lines)


def build_prompt(query: str, context: str) -> str:
    return f"""Du bist ein Hörspiel-Experte und hilfst dabei, passende Hörspiele zu entdecken.
Dir werden Hörspiele aus einer Datenbank bereitgestellt die semantisch zur Anfrage passen.
Empfiehl die passendsten davon und erkläre kurz warum sie zur Anfrage passen.
Antworte auf Deutsch, freundlich und enthusiastisch.
Wenn keines der Hörspiele wirklich passt, sag das ehrlich.

Anfrage: {query}

Gefundene Hörspiele:
{context}

Empfehlung:"""


def ask(
    query: str,
    match_count: int = 10,
    filter_genre: str | None = None,
) -> dict:
    """
    Full RAG pipeline:
    1. Embed the query
    2. Search for similar episodes
    3. Build context
    4. Generate response with Gemini
    """
    openai   = get_openai_client()
    supabase = get_supabase_client()
    gemini   = get_gemini_client()

    # 1. Embed query
    query_embedding = embed_query(openai, query)

    # 2. Vector search
    episodes = search_episodes(supabase, query_embedding, match_count, filter_genre)

    # 3. Build context + prompt
    context = build_context(episodes)
    prompt  = build_prompt(query, context)

    # 4. Generate response
    response = gemini.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt,
    )

    return {
        "query":    query,
        "response": response.text,
        "episodes": episodes,
    }


if __name__ == "__main__":
    result = ask("Empfiehl mir ein Abenteuer-Hörspiel mit jungen Protagonisten. " \
                    "Die Geschichte soll im Freien spielen – zum Beispiel auf einer " \
                    "geheimnisvollen Insel oder bei der Suche nach einem versteckten Schatz. " \
                    "Aktivitäten wie Tauchen und Klettern sollen vorkommen.")
    print(result["response"])
    print("\n--- Retrieved episodes ---")
    for ep in result["episodes"]:
        print(f"  {ep['title']} ({ep['series_name']}) — similarity: {ep['similarity']:.3f}")