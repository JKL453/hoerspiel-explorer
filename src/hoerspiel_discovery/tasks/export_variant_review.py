from __future__ import annotations

import csv
import json
import os
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from prefect import get_run_logger, task

from hoerspiel_discovery.config import EPISODE_VARIANT_REVIEW_DIR


REQUIRED_DBT_ENV = ("DBT_HOST", "DBT_USER", "DBT_PASSWORD")
REVIEW_DECISIONS = ("accept", "reject", "uncertain")
CANDIDATE_COLUMNS = (
    "candidate_id",
    "source_episode_id",
    "source_key",
    "source_title",
    "variant_category",
    "target_episode_id",
    "target_source_key",
    "target_title",
    "target_episode_number",
    "proposed_relationship",
    "confidence_score",
    "confidence_class",
    "match_reasons",
    "edition_markers",
    "range_start",
    "range_end",
)
CSV_COLUMNS = (
    "candidate_id",
    "generated_at",
    *CANDIDATE_COLUMNS[1:],
    "review_decision",
    "review_note",
)


def _validate_environment() -> None:
    missing = [name for name in REQUIRED_DBT_ENV if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing dbt environment variables: {', '.join(missing)}")


def _connect():
    _validate_environment()
    import psycopg2

    return psycopg2.connect(
        host=os.environ["DBT_HOST"],
        port=int(os.environ.get("DBT_PORT", "5432")),
        user=os.environ["DBT_USER"],
        password=os.environ["DBT_PASSWORD"],
        dbname=os.environ.get("DBT_DBNAME", "postgres"),
        sslmode=os.environ.get("DBT_SSLMODE", "require"),
        connect_timeout=15,
        application_name="hoerspiel-variant-review-export",
    )


def _fetch_candidates(connection) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute("SET TRANSACTION READ ONLY")
        cursor.execute(
            """
            SELECT
                candidate_id,
                source_episode_id,
                source_key,
                source_title,
                variant_category,
                target_episode_id,
                target_source_key,
                target_title,
                target_episode_number,
                proposed_relationship,
                confidence_score,
                confidence_class,
                match_reasons,
                edition_markers,
                range_start,
                range_end
            FROM analytics.episode_variant_candidates
            ORDER BY
                CASE confidence_class
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    ELSE 3
                END,
                variant_category,
                source_episode_id,
                target_episode_number NULLS LAST,
                candidate_id
            """
        )
        columns = tuple(item.name for item in cursor.description)
        if columns != CANDIDATE_COLUMNS:
            raise RuntimeError(
                "Unexpected episode variant candidate schema: " + ", ".join(columns)
            )
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _validate_candidates(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    materialized = list(rows)
    if not materialized:
        raise RuntimeError("Episode variant candidate model is empty")

    candidate_ids = [row.get("candidate_id") for row in materialized]
    if any(not candidate_id for candidate_id in candidate_ids):
        raise RuntimeError("Episode variant candidates contain an empty candidate_id")
    if len(candidate_ids) != len(set(candidate_ids)):
        raise RuntimeError("Episode variant candidates contain duplicate candidate_ids")

    invalid_scores = [
        row["candidate_id"]
        for row in materialized
        if not 0 <= int(row["confidence_score"]) <= 100
    ]
    if invalid_scores:
        raise RuntimeError(f"Invalid confidence scores: {invalid_scores[:5]}")
    return materialized


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return value


def _write_latest_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}-", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as temporary_file:
            json.dump(payload, temporary_file, ensure_ascii=False, indent=2)
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _export_rows(
    rows: Iterable[dict[str, Any]],
    destination: Path,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    candidates = _validate_candidates(rows)
    timestamp = generated_at or datetime.now(UTC)
    timestamp = timestamp.astimezone(UTC)
    iso_timestamp = timestamp.isoformat().replace("+00:00", "Z")
    filename_timestamp = timestamp.strftime("%Y%m%dT%H%M%S%fZ")
    destination.mkdir(parents=True, exist_ok=True)
    csv_path = destination / f"die_drei_fragezeichen_{filename_timestamp}.csv"

    with csv_path.open("x", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for candidate in candidates:
            output = {key: _csv_value(value) for key, value in candidate.items()}
            output.update(
                generated_at=iso_timestamp,
                review_decision="",
                review_note="",
            )
            writer.writerow(output)

    stats = {
        "records": len(candidates),
        "categories": dict(Counter(row["variant_category"] for row in candidates)),
        "relationships": dict(
            Counter(row["proposed_relationship"] for row in candidates)
        ),
        "confidence": dict(Counter(row["confidence_class"] for row in candidates)),
        "unresolved": sum(
            row["proposed_relationship"] == "unresolved" for row in candidates
        ),
    }
    manifest = {
        "generated_at": iso_timestamp,
        "csv_path": str(csv_path),
        "allowed_review_decisions": list(REVIEW_DECISIONS),
        "stats": stats,
    }
    _write_latest_manifest(destination / "latest.json", manifest)
    return manifest


@task(name="export-episode-variant-review-csv")
def export_episode_variant_review_csv() -> dict[str, Any]:
    logger = get_run_logger()
    connection = _connect()
    try:
        rows = _fetch_candidates(connection)
        connection.rollback()
    finally:
        connection.close()

    result = _export_rows(rows, EPISODE_VARIANT_REVIEW_DIR)
    stats = result["stats"]
    logger.info("Published review CSV: %s", result["csv_path"])
    logger.info("Candidate categories: %s", stats["categories"])
    logger.info("Proposed relationships: %s", stats["relationships"])
    logger.info("Confidence classes: %s", stats["confidence"])
    logger.info("Unresolved source records: %s", stats["unresolved"])
    return result
