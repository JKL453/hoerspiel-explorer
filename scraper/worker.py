"""
Scraper worker mit Pause/Resume-Unterstützung.
State lebt im RAM — kein DB-Write, nur HTML-Files + JSON.
"""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from hoerspiel_discovery.scraper.fetch_series import (
    fetch_page,
    extract_episode_links,
    save_html,
    build_file_name,
    polite_delay,
)
from hoerspiel_discovery.parser.parse_detail import parse_detail_page, load_html
from hoerspiel_discovery.cleaner.clean_detail import clean_detail_record
from hoerspiel_discovery.config import (
    RAW_DETAIL_PAGES_DIR,
    RAW_SERIES_PAGES_DIR,
    INTERIM_DATA_DIR,
)

logger = logging.getLogger("hoerspiel.worker")

Status = Literal["idle", "running", "paused", "done", "error"]


@dataclass
class EpisodeResult:
    url: str
    title: str
    status: Literal["ok", "skip", "error"]
    message: str = ""
    ts: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


@dataclass
class JobState:
    series_id: int
    series_url: str
    status: Status = "idle"
    total: int = 0
    done: int = 0
    skipped: int = 0
    errors: int = 0
    current_title: str = ""
    log: list[EpisodeResult] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""

    def to_dict(self) -> dict:
        return {
            "series_id": self.series_id,
            "series_url": self.series_url,
            "status": self.status,
            "total": self.total,
            "done": self.done,
            "skipped": self.skipped,
            "errors": self.errors,
            "current_title": self.current_title,
            "log": [
                {"url": e.url, "title": e.title, "status": e.status, "message": e.message, "ts": e.ts}
                for e in self.log[-200:]  # letzten 200 Einträge
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


class ScraperWorker:
    def __init__(self, delay: float = 3.0):
        self.delay = delay
        self._jobs: dict[int, JobState] = {}
        self._pause_event = threading.Event()
        self._pause_event.set()  # nicht pausiert = set
        self._lock = threading.Lock()
        self._active_thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enqueue(self, series_ids: list[int]) -> None:
        with self._lock:
            for sid in series_ids:
                if sid not in self._jobs:
                    url = f"https://www.hoerspiele.de/hsp_serie.asp?serie={sid}"
                    self._jobs[sid] = JobState(series_id=sid, series_url=url)

        if self._active_thread is None or not self._active_thread.is_alive():
            self._active_thread = threading.Thread(target=self._run_all, daemon=True)
            self._active_thread.start()

    def pause(self) -> None:
        self._pause_event.clear()
        logger.info("Scraper pausiert")

    def resume(self) -> None:
        self._pause_event.set()
        logger.info("Scraper fortgesetzt")
        # Falls Thread fertig ist aber noch idle Jobs vorhanden → neu starten
        if self._active_thread is None or not self._active_thread.is_alive():
            self._active_thread = threading.Thread(target=self._run_all, daemon=True)
            self._active_thread.start()

    def is_paused(self) -> bool:
        return not self._pause_event.is_set()

    def get_state(self) -> dict:
        with self._lock:
            return {
                "paused": self.is_paused(),
                "jobs": [j.to_dict() for j in self._jobs.values()],
            }

    def get_summary(self) -> dict:
        """Schnelle Zusammenfassung für die Stats-Leiste."""
        with self._lock:
            total_eps = sum(j.done + j.skipped for j in self._jobs.values())
            running = sum(1 for j in self._jobs.values() if j.status == "running")
            done = sum(1 for j in self._jobs.values() if j.status == "done")
            errors = sum(j.errors for j in self._jobs.values())
            return {
                "total_episodes": total_eps,
                "jobs_total": len(self._jobs),
                "jobs_running": running,
                "jobs_done": done,
                "total_errors": errors,
                "paused": self.is_paused(),
            }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_all(self) -> None:
        while True:
            with self._lock:
                pending = [j for j in self._jobs.values() if j.status == "idle"]
            if not pending:
                break
            self._scrape_series(pending[0])

    def _scrape_series(self, job: JobState) -> None:
        job.status = "running"
        job.started_at = datetime.now().isoformat(timespec="seconds")
        logger.info(f"Starte Serie {job.series_id}")

        # 1. Series-Seite fetchen
        try:
            self._pause_event.wait()
            html = fetch_page(job.series_url)
            save_html(html, RAW_SERIES_PAGES_DIR, job.series_url)
        except Exception as e:
            job.status = "error"
            job.finished_at = datetime.now().isoformat(timespec="seconds")
            logger.error(f"Fehler beim Laden der Serien-Seite: {e}")
            return

        episode_links = extract_episode_links(html, base_url=job.series_url)
        job.total = len(episode_links)
        logger.info(f"Serie {job.series_id}: {job.total} Episoden gefunden")

        parsed_records: list[dict] = []

        # 2. Episoden fetchen + parsen + cleanen
        for ep in episode_links:
            # Pause abwarten (blockiert bis resume())
            self._pause_event.wait()

            url = ep["url"]
            title = ep["title"]
            job.current_title = title

            file_name = build_file_name(url)
            output_path = RAW_DETAIL_PAGES_DIR / file_name

            if output_path.exists():
                # Schon vorhanden → nur parsen
                try:
                    ep_html = load_html(output_path)
                    parsed = parse_detail_page(ep_html)
                    parsed["source_url"] = url
                    cleaned = clean_detail_record(parsed)
                    parsed_records.append(cleaned)
                    job.skipped += 1
                    job.log.append(EpisodeResult(url=url, title=title, status="skip"))
                    logger.debug(f"Skip (existiert): {title}")
                except Exception as e:
                    job.errors += 1
                    job.log.append(EpisodeResult(url=url, title=title, status="error", message=str(e)))
                continue

            # Fetch
            try:
                polite_delay(self.delay)
                self._pause_event.wait()  # nochmal prüfen nach dem Sleep
                ep_html = fetch_page(url)
                save_html(ep_html, RAW_DETAIL_PAGES_DIR, url)
            except Exception as e:
                job.errors += 1
                job.log.append(EpisodeResult(url=url, title=title, status="error", message=str(e)))
                logger.error(f"Fetch-Fehler {url}: {e}")
                continue

            # Parse + Clean
            try:
                parsed = parse_detail_page(ep_html)
                parsed["source_url"] = url
                cleaned = clean_detail_record(parsed)
                parsed_records.append(cleaned)
                job.done += 1
                job.log.append(EpisodeResult(url=url, title=title, status="ok"))
            except Exception as e:
                job.errors += 1
                job.log.append(EpisodeResult(url=url, title=title, status="error", message=str(e)))
                logger.error(f"Parse-Fehler {url}: {e}")

        # 3. JSON schreiben
        self._write_json(job.series_id, parsed_records)

        job.status = "done"
        job.current_title = ""
        job.finished_at = datetime.now().isoformat(timespec="seconds")
        logger.info(f"Serie {job.series_id} fertig: {job.done} neu, {job.skipped} übersprungen, {job.errors} Fehler")

    def _write_json(self, series_id: int, records: list[dict]) -> None:
        INTERIM_DATA_DIR.mkdir(parents=True, exist_ok=True)
        out = INTERIM_DATA_DIR / f"cleaned_series_{series_id}.json"
        out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"JSON geschrieben: {out}")


# Singleton — wird von app.py und run_scraper.py geteilt
worker = ScraperWorker()