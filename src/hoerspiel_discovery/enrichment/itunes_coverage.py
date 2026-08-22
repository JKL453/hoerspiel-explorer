from __future__ import annotations

import hashlib
import json
import os
import re
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import requests
import certifi

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
RESULT_LIMIT = 200
MIN_REQUEST_INTERVAL_SECONDS = 3.1
EPISODE_NUMBER_RE = re.compile(r"\b(?:folge|episode)\s*(\d{1,3})\b", re.I)


@dataclass(frozen=True)
class SeriesProbe:
    key: str
    name: str
    search_term: str
    artist_aliases: tuple[str, ...]


SERIES_PROBES = (
    SeriesProbe("die-drei-fragezeichen", "Die drei ???", "Die drei Fragezeichen", ("Die drei ???",)),
    SeriesProbe("tkkg", "TKKG", "TKKG", ("TKKG",)),
    SeriesProbe("bibi-blocksberg", "Bibi Blocksberg", "Bibi Blocksberg", ("Bibi Blocksberg",)),
    SeriesProbe("benjamin-bluemchen", "Benjamin Blümchen", "Benjamin Blümchen", ("Benjamin Blümchen",)),
    SeriesProbe("john-sinclair", "John Sinclair", "John Sinclair", ("John Sinclair",)),
    SeriesProbe("die-drei-fragezeichen-kids", "Die drei ??? Kids", "Die drei Fragezeichen Kids", ("Die drei ??? Kids",)),
    SeriesProbe("fuenf-freunde", "Fünf Freunde", "Fünf Freunde", ("Fünf Freunde",)),
    SeriesProbe("hanni-und-nanni", "Hanni und Nanni", "Hanni und Nanni", ("Hanni und Nanni",)),
    SeriesProbe("hui-buh", "Hui Buh", "Hui Buh", ("HUI BUH neue Welt", "Hui Buh")),
    SeriesProbe("pumuckl", "Pumuckl", "Pumuckl", ("Pumuckl",)),
    SeriesProbe("teufelskicker", "Teufelskicker", "Teufelskicker", ("Teufelskicker",)),
    SeriesProbe("die-playmos", "Die Playmos", "Die Playmos", ("Die Playmos",)),
    SeriesProbe("gruselkabinett", "Gruselkabinett", "Gruselkabinett", ("Gruselkabinett",)),
    SeriesProbe("offenbarung-23", "Offenbarung 23", "Offenbarung 23", ("Offenbarung 23",)),
    SeriesProbe("gabriel-burns", "Gabriel Burns", "Gabriel Burns", ("Gabriel Burns",)),
    SeriesProbe("point-whitmark", "Point Whitmark", "Point Whitmark", ("Point Whitmark",)),
    SeriesProbe("geisterjaeger-john-sinclair", "Geisterjäger John Sinclair", "Geisterjäger John Sinclair", ("Geisterjäger John Sinclair", "John Sinclair")),
    SeriesProbe("was-ist-was", "WAS IST WAS", "WAS IST WAS Hörspiel", ("WAS IST WAS",)),
    SeriesProbe("wendy", "Wendy", "Wendy Hörspiel", ("Wendy",)),
    SeriesProbe("feuerwehrmann-sam", "Feuerwehrmann Sam", "Feuerwehrmann Sam Hörspiel", ("Feuerwehrmann Sam",)),
)


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = decomposed.encode("ascii", "ignore").decode("ascii")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", ascii_value.lower()).split())


class ItunesSearchClient:
    def __init__(
        self,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.session = session or requests.Session()
        self.sleep = sleep
        self.clock = clock
        self._last_request_at: float | None = None

    def _throttle(self) -> None:
        if self._last_request_at is None:
            return
        remaining = MIN_REQUEST_INTERVAL_SECONDS - (
            self.clock() - self._last_request_at
        )
        if remaining > 0:
            self.sleep(remaining)

    def search_albums(self, term: str, attempts: int = 3) -> dict[str, Any]:
        params = {
            "term": term,
            "country": "DE",
            "media": "music",
            "entity": "album",
            "limit": RESULT_LIMIT,
        }
        headers = {
            "User-Agent": "hoerspiel-explorer-coverage-pilot/1.0 (portfolio research)",
            "Accept": "application/json",
        }
        for attempt in range(1, attempts + 1):
            self._throttle()
            try:
                response = self.session.get(
                    ITUNES_SEARCH_URL,
                    params=params,
                    headers=headers,
                    timeout=30,
                    verify=certifi.where(),
                )
                self._last_request_at = self.clock()
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt == attempts:
                        response.raise_for_status()
                    delay = float(response.headers.get("Retry-After", 2**attempt))
                    self.sleep(delay)
                    continue
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload.get("results"), list):
                    raise ValueError("iTunes response has no results list")
                return payload
            except requests.RequestException:
                if attempt == attempts:
                    raise
                self.sleep(2**attempt)
        raise RuntimeError("unreachable")


def _is_candidate(result: dict[str, Any], probe: SeriesProbe) -> bool:
    artist = normalize(str(result.get("artistName", "")))
    title = normalize(str(result.get("collectionName", "")))
    aliases = {normalize(alias) for alias in probe.artist_aliases}
    series_name = normalize(probe.name)
    return artist in aliases or (series_name and series_name in title)


def analyze_probe(probe: SeriesProbe, payload: dict[str, Any]) -> dict[str, Any]:
    results = payload["results"]
    candidate_by_id: dict[str, dict[str, Any]] = {}
    for result in results:
        if not _is_candidate(result, probe):
            continue
        identifier = str(result.get("collectionId", ""))
        if identifier:
            candidate_by_id[identifier] = result
    candidates = list(candidate_by_id.values())
    titles = [str(item.get("collectionName", "")) for item in candidates]
    normalized_title_counts = Counter(normalize(title) for title in titles if title)
    duplicate_title_groups = sum(count > 1 for count in normalized_title_counts.values())
    numbered = [
        int(match.group(1))
        for title in titles
        if (match := EPISODE_NUMBER_RE.search(title))
    ]
    years = []
    for item in candidates:
        release_date = str(item.get("releaseDate", ""))
        if len(release_date) >= 4 and release_date[:4].isdigit():
            years.append(int(release_date[:4]))
    examples = [
        {
            "collection_id": item.get("collectionId"),
            "title": item.get("collectionName"),
            "artist": item.get("artistName"),
            "release_date": item.get("releaseDate"),
            "track_count": item.get("trackCount"),
            "store_url": item.get("collectionViewUrl"),
        }
        for item in sorted(candidates, key=lambda row: str(row.get("collectionId")))[:5]
    ]
    return {
        "series_key": probe.key,
        "series_name": probe.name,
        "search_term": probe.search_term,
        "returned_count": len(results),
        "candidate_count": len(candidates),
        "numbered_count": len(numbered),
        "distinct_episode_numbers": len(set(numbered)),
        "duplicate_title_groups": duplicate_title_groups,
        "earliest_year": min(years) if years else None,
        "latest_year": max(years) if years else None,
        "result_limit_reached": len(results) >= RESULT_LIMIT,
        "examples": examples,
    }


def build_coverage_report(
    client: ItunesSearchClient,
    probes: tuple[SeriesProbe, ...] = SERIES_PROBES,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    analyses = []
    for index, probe in enumerate(probes, start=1):
        if progress:
            progress(f"[{index}/{len(probes)}] Querying {probe.name}")
        analyses.append(analyze_probe(probe, client.search_albums(probe.search_term)))
    generated_at = datetime.now(UTC).isoformat()
    report = {
        "report_version": 1,
        "generated_at": generated_at,
        "source": {
            "name": "Apple iTunes Search API",
            "endpoint": ITUNES_SEARCH_URL,
            "country": "DE",
            "media": "music",
            "entity": "album",
            "result_limit": RESULT_LIMIT,
            "purpose": "private coverage evaluation; no Supabase ingestion",
        },
        "summary": {
            "queries": len(analyses),
            "returned_results": sum(row["returned_count"] for row in analyses),
            "candidate_results": sum(row["candidate_count"] for row in analyses),
            "distinct_numbered_episodes": sum(
                row["distinct_episode_numbers"] for row in analyses
            ),
            "limit_reached_queries": sum(
                row["result_limit_reached"] for row in analyses
            ),
        },
        "series": analyses,
    }
    canonical = json.dumps(report["series"], ensure_ascii=False, sort_keys=True)
    report["content_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return report


def publish_report(report: dict[str, Any], destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.fromisoformat(report["generated_at"]).strftime("%Y%m%dT%H%M%SZ")
    report_path = destination / f"itunes_coverage_{timestamp}.json"
    if report_path.exists():
        raise FileExistsError(f"Coverage report already exists: {report_path}")
    temporary = destination / f".{report_path.name}.tmp"
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, report_path)
    latest = destination / "latest.json"
    latest_temporary = destination / ".latest.json.tmp"
    latest_temporary.write_text(
        json.dumps(
            {
                "report": report_path.name,
                "generated_at": report["generated_at"],
                "content_sha256": report["content_sha256"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    os.replace(latest_temporary, latest)
    return report_path
