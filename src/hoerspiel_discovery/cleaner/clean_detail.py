from __future__ import annotations

import re
from typing import Any


UNWANTED_GENRES = {
    "Award-Verdächtig!",
}


def normalize_whitespace(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = " ".join(value.split())
    return cleaned or None


def fix_common_mojibake(value: str | None) -> str | None:
    if value is None:
        return None

    replacements = {
        "": '"',
        "": '"',
        "": "'",
        "": "...",
        "": "-",
        "–": "-",
        "—": "-",
    }

    cleaned = value
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)

    return cleaned


def clean_text(value: str | None) -> str | None:
    value = fix_common_mojibake(value)
    value = normalize_whitespace(value)
    return value


def clean_order_number(value: str | None) -> str | None:
    value = clean_text(value)
    if value is None:
        return None

    # offensichtliche Parser-Fehler wie "CD."
    if value.upper() in {"CD.", "CD", "MC.", "MC"}:
        return None

    # nur sinnvolle Bestellnummern behalten
    if len(value) < 5:
        return None

    return value


def clean_genres(genres: list[str] | None) -> list[str]:
    if not genres:
        return []

    cleaned_genres: list[str] = []
    seen: set[str] = set()

    for genre in genres:
        cleaned = clean_text(genre)
        if cleaned is None:
            continue

        if cleaned in UNWANTED_GENRES:
            continue

        if cleaned in seen:
            continue

        seen.add(cleaned)
        cleaned_genres.append(cleaned)

    return cleaned_genres


def clean_person_name(name: str | None) -> str | None:
    return clean_text(name)


def clean_role_name(role: str | None) -> str | None:
    return clean_text(role)


def clean_speakers(speakers: list[dict[str, str]] | None) -> list[dict[str, str]]:
    if not speakers:
        return []

    cleaned_speakers: list[dict[str, str]] = []

    for entry in speakers:
        role = clean_role_name(entry.get("role"))
        speaker = clean_person_name(entry.get("speaker"))

        if role is None or speaker is None:
            continue

        cleaned_speakers.append(
            {
                "role": role,
                "speaker": speaker,
            }
        )

    return cleaned_speakers


def clean_url(value: str | None) -> str | None:
    return clean_text(value)


def clean_detail_record(record: dict[str, Any]) -> dict[str, Any]:
    cleaned = {
        "title": clean_text(record.get("title")),
        "series_name": clean_text(record.get("series_name")),
        "episode_number": record.get("episode_number"),
        "description": clean_text(record.get("description")),
        "duration_minutes": record.get("duration_minutes"),
        "release_date": clean_text(record.get("release_date")),
        "label": clean_text(record.get("label")),
        "cover_url": clean_url(record.get("cover_url")),
        "speakers": clean_speakers(record.get("speakers")),
        "order_number": clean_order_number(record.get("order_number")),
        "genres": clean_genres(record.get("genres")),
        "previous_episode_url": clean_url(record.get("previous_episode_url")),
        "next_episode_url": clean_url(record.get("next_episode_url")),
        "source_url": clean_text(record.get("source_url")),
    }

    return cleaned