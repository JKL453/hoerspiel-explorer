"""
Scraper worker mit Pause/Resume-Unterstützung und persistentem State.
State wird atomar auf Disk gespeichert — resume nach Container-Neustart möglich.
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
    DATA_DIR,
    RAW_DETAIL_PAGES_DIR,
    RAW_SERIES_PAGES_DIR,
    INTERIM_DATA_DIR,
)

logger = logging.getLogger("hoerspiel.worker")

SERIES_BASE_URL = "https://www.hoerspiele.de/hsp_serie.asp?serie={}"
STATE_FILE = DATA_DIR / "scraper_state.json"
INDEX_FILE = DATA_DIR / "series_index.json"

Status = Literal["idle", "running", "paused", "done", "error"]


@dataclass
class EpisodeResult:
    url: str
    title: str
    status: Literal["ok", "skip", "error"]
    message: str = ""
    ts: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


@dataclass
class DiscoveryState:
    status: Literal["idle", "running", "done"] = "idle"
    current_id: int = 0
    max_id: int = 2000
    valid: list[int] = field(default_factory=list)
    consecutive_misses: int = 0
    stop_after_misses: int = 50
    scrape_after: bool = False
    started_at: str = ""
    finished_at: str = ""

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "current_id": self.current_id,
            "max_id": self.max_id,
            "valid": self.valid,
            "consecutive_misses": self.consecutive_misses,
            "stop_after_misses": self.stop_after_misses,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DiscoveryState":
        obj = cls()
        obj.status = d.get("status", "idle")
        if obj.status == "running":
            obj.status = "idle"  # interrupted — will resume on next start_discovery call
        obj.current_id = d.get("current_id", 0)
        obj.max_id = d.get("max_id", 2000)
        obj.valid = d.get("valid", [])
        obj.consecutive_misses = d.get("consecutive_misses", 0)
        obj.stop_after_misses = d.get("stop_after_misses", 50)
        obj.started_at = d.get("started_at", "")
        obj.finished_at = d.get("finished_at", "")
        return obj


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
                for e in self.log[-200:]
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "JobState":
        obj = cls(series_id=d["series_id"], series_url=d["series_url"])
        obj.status = d.get("status", "idle")
        if obj.status == "running":
            obj.status = "idle"  # interrupted — re-queue
        obj.total = d.get("total", 0)
        obj.done = d.get("done", 0)
        obj.skipped = d.get("skipped", 0)
        obj.errors = d.get("errors", 0)
        obj.current_title = ""
        obj.log = [
            EpisodeResult(
                url=e["url"], title=e["title"], status=e["status"],
                message=e.get("message", ""), ts=e.get("ts", ""),
            )
            for e in d.get("log", [])
        ]
        obj.started_at = d.get("started_at", "")
        obj.finished_at = d.get("finished_at", "")
        return obj


class ScraperWorker:
    def __init__(self, delay: float = 3.0):
        self.delay = delay
        self._jobs: dict[int, JobState] = {}
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._lock = threading.Lock()
        self._active_thread: threading.Thread | None = None
        self._discovery = DiscoveryState()
        self._discovery_thread: threading.Thread | None = None
        self._load_state()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enqueue(self, series_ids: list[int]) -> None:
        with self._lock:
            for sid in series_ids:
                if sid not in self._jobs:
                    self._jobs[sid] = JobState(series_id=sid, series_url=SERIES_BASE_URL.format(sid))
        self._save_state()
        self._ensure_scrape_thread()

    def start_discovery(self, max_id: int = 2000, delay: float = 1.0, stop_after_misses: int = 50) -> None:
        if self._discovery_thread and self._discovery_thread.is_alive():
            return
        self._discovery.status = "running"
        self._discovery.max_id = max_id
        self._discovery.stop_after_misses = stop_after_misses
        if not self._discovery.started_at:
            self._discovery.started_at = datetime.now().isoformat(timespec="seconds")
        self._discovery_thread = threading.Thread(
            target=self._run_discovery, args=(delay,), daemon=True
        )
        self._discovery_thread.start()

    def scrape_all(self, max_id: int = 2000, delay: float = 1.0, stop_after_misses: int = 50) -> None:
        if self._discovery.status == "done":
            with self._lock:
                new_ids = [sid for sid in self._discovery.valid if sid not in self._jobs]
            if new_ids:
                self.enqueue(new_ids)
        else:
            self._discovery.scrape_after = True
            self.start_discovery(max_id=max_id, delay=delay, stop_after_misses=stop_after_misses)

    def pause(self) -> None:
        self._pause_event.clear()
        logger.info("Scraper pausiert")

    def resume(self) -> None:
        self._pause_event.set()
        logger.info("Scraper fortgesetzt")
        self._ensure_scrape_thread()

    def is_paused(self) -> bool:
        return not self._pause_event.is_set()

    def get_state(self) -> dict:
        with self._lock:
            return {
                "paused": self.is_paused(),
                "jobs": [j.to_dict() for j in self._jobs.values()],
                "discovery": self._discovery.to_dict(),
            }

    def get_summary(self) -> dict:
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
                "discovery_status": self._discovery.status,
                "discovery_found": len(self._discovery.valid),
                "discovery_current_id": self._discovery.current_id,
                "discovery_max_id": self._discovery.max_id,
            }

    # ------------------------------------------------------------------
    # Internal — Discovery
    # ------------------------------------------------------------------

    def _run_discovery(self, delay: float) -> None:
        start_id = self._discovery.current_id + 1
        logger.info(f"Discovery startet bei ID {start_id}, max {self._discovery.max_id}")

        for sid in range(start_id, self._discovery.max_id + 1):
            self._pause_event.wait()

            self._discovery.current_id = sid
            if self._check_series_exists(sid):
                if sid not in self._discovery.valid:
                    self._discovery.valid.append(sid)
                self._discovery.consecutive_misses = 0
                logger.debug(f"Serie {sid}: gefunden")
            else:
                self._discovery.consecutive_misses += 1
                logger.debug(f"Serie {sid}: nicht gefunden ({self._discovery.consecutive_misses} in Folge)")

            self._save_index()

            if self._discovery.consecutive_misses >= self._discovery.stop_after_misses:
                logger.info(f"Discovery stoppt nach {self._discovery.stop_after_misses} aufeinanderfolgenden Misses")
                break

            polite_delay(delay)

        self._discovery.status = "done"
        self._discovery.finished_at = datetime.now().isoformat(timespec="seconds")
        self._save_index()
        logger.info(f"Discovery abgeschlossen: {len(self._discovery.valid)} Serien gefunden")

        if self._discovery.scrape_after:
            with self._lock:
                new_ids = [sid for sid in self._discovery.valid if sid not in self._jobs]
            if new_ids:
                self.enqueue(new_ids)

    def _check_series_exists(self, series_id: int) -> bool:
        try:
            html = fetch_page(SERIES_BASE_URL.format(series_id))
            return len(extract_episode_links(html, base_url=SERIES_BASE_URL.format(series_id))) > 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Internal — Scraping
    # ------------------------------------------------------------------

    def _ensure_scrape_thread(self) -> None:
        if self._active_thread is None or not self._active_thread.is_alive():
            with self._lock:
                has_idle = any(j.status == "idle" for j in self._jobs.values())
            if has_idle:
                self._active_thread = threading.Thread(target=self._run_all, daemon=True)
                self._active_thread.start()

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

        try:
            self._pause_event.wait()
            html = fetch_page(job.series_url)
            save_html(html, RAW_SERIES_PAGES_DIR, job.series_url)
        except Exception as e:
            job.status = "error"
            job.finished_at = datetime.now().isoformat(timespec="seconds")
            self._save_state()
            logger.error(f"Fehler beim Laden der Serien-Seite: {e}")
            return

        episode_links = extract_episode_links(html, base_url=job.series_url)
        job.total = len(episode_links)
        logger.info(f"Serie {job.series_id}: {job.total} Episoden gefunden")

        parsed_records: list[dict] = []

        for ep in episode_links:
            self._pause_event.wait()

            url = ep["url"]
            title = ep["title"]
            job.current_title = title

            output_path = RAW_DETAIL_PAGES_DIR / build_file_name(url)

            if output_path.exists():
                try:
                    ep_html = load_html(output_path)
                    parsed = parse_detail_page(ep_html)
                    parsed["source_url"] = url
                    cleaned = clean_detail_record(parsed)
                    parsed_records.append(cleaned)
                    job.skipped += 1
                    job.log.append(EpisodeResult(url=url, title=title, status="skip"))
                except Exception as e:
                    job.errors += 1
                    job.log.append(EpisodeResult(url=url, title=title, status="error", message=str(e)))
                self._save_state()
                continue

            try:
                polite_delay(self.delay)
                self._pause_event.wait()
                ep_html = fetch_page(url)
                save_html(ep_html, RAW_DETAIL_PAGES_DIR, url)
            except Exception as e:
                job.errors += 1
                job.log.append(EpisodeResult(url=url, title=title, status="error", message=str(e)))
                self._save_state()
                logger.error(f"Fetch-Fehler {url}: {e}")
                continue

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

            self._save_state()

        self._write_json(job.series_id, parsed_records)
        job.status = "done"
        job.current_title = ""
        job.finished_at = datetime.now().isoformat(timespec="seconds")
        self._save_state()
        logger.info(f"Serie {job.series_id} fertig: {job.done} neu, {job.skipped} übersprungen, {job.errors} Fehler")

    def _write_json(self, series_id: int, records: list[dict]) -> None:
        INTERIM_DATA_DIR.mkdir(parents=True, exist_ok=True)
        out = INTERIM_DATA_DIR / f"cleaned_series_{series_id}.json"
        out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"JSON geschrieben: {out}")

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _atomic_write(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def _save_state(self) -> None:
        with self._lock:
            data = {"jobs": [j.to_dict() for j in self._jobs.values()]}
        try:
            self._atomic_write(STATE_FILE, data)
        except Exception as e:
            logger.warning(f"State konnte nicht gespeichert werden: {e}")

    def _save_index(self) -> None:
        try:
            self._atomic_write(INDEX_FILE, self._discovery.to_dict())
        except Exception as e:
            logger.warning(f"Index konnte nicht gespeichert werden: {e}")

    def _load_state(self) -> None:
        if INDEX_FILE.exists():
            try:
                self._discovery = DiscoveryState.from_dict(
                    json.loads(INDEX_FILE.read_text(encoding="utf-8"))
                )
                logger.info(f"Discovery-Index geladen: {len(self._discovery.valid)} bekannte Serien, Status: {self._discovery.status}")
            except Exception as e:
                logger.warning(f"Index konnte nicht geladen werden: {e}")

        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                for job_dict in data.get("jobs", []):
                    job = JobState.from_dict(job_dict)
                    self._jobs[job.series_id] = job
                logger.info(f"State geladen: {len(self._jobs)} Jobs")
            except Exception as e:
                logger.warning(f"State konnte nicht geladen werden: {e}")

        self._ensure_scrape_thread()


# Singleton — wird von app.py und run_scraper.py geteilt
worker = ScraperWorker()
