import csv
import json
from datetime import UTC, datetime

import pytest

from hoerspiel_discovery.tasks import export_variant_review


def _candidate(candidate_id="candidate-1"):
    return {
        "candidate_id": candidate_id,
        "source_episode_id": 10,
        "source_key": "hoerspiele.de:episode:10",
        "source_title": "Fanbox (Folgen 01-03)",
        "variant_category": "box_set",
        "target_episode_id": 1,
        "target_source_key": "hoerspiele.de:episode:1",
        "target_title": "und der Super-Papagei",
        "target_episode_number": 1,
        "proposed_relationship": "contains",
        "confidence_score": 100,
        "confidence_class": "high",
        "match_reasons": ["explicit_episode_range"],
        "edition_markers": "fanbox",
        "range_start": 1,
        "range_end": 3,
    }


def test_environment_validation_lists_missing_values(monkeypatch):
    for name in export_variant_review.REQUIRED_DBT_ENV:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeError, match="DBT_HOST, DBT_USER, DBT_PASSWORD"):
        export_variant_review._validate_environment()


def test_candidate_validation_rejects_empty_and_duplicate_ids():
    with pytest.raises(RuntimeError, match="empty"):
        export_variant_review._validate_candidates([])
    with pytest.raises(RuntimeError, match="duplicate"):
        export_variant_review._validate_candidates([_candidate(), _candidate()])


def test_export_is_non_overwriting_and_writes_review_columns(tmp_path):
    timestamp = datetime(2026, 8, 12, 12, 30, 45, 123456, tzinfo=UTC)
    result = export_variant_review._export_rows([_candidate()], tmp_path, timestamp)
    csv_path = tmp_path / "die_drei_fragezeichen_20260812T123045123456Z.csv"

    assert result["csv_path"] == str(csv_path)
    assert result["stats"] == {
        "records": 1,
        "categories": {"box_set": 1},
        "relationships": {"contains": 1},
        "confidence": {"high": 1},
        "unresolved": 0,
    }
    with csv_path.open(encoding="utf-8", newline="") as csv_file:
        row = next(csv.DictReader(csv_file))
    assert row["review_decision"] == ""
    assert row["review_note"] == ""
    assert json.loads(row["match_reasons"]) == ["explicit_episode_range"]

    latest = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert latest["csv_path"] == str(csv_path)
    assert latest["allowed_review_decisions"] == ["accept", "reject", "uncertain"]

    with pytest.raises(FileExistsError):
        export_variant_review._export_rows([_candidate()], tmp_path, timestamp)


def test_export_keeps_unresolved_candidates_visible(tmp_path):
    candidate = _candidate()
    candidate.update(
        candidate_id="unresolved-1",
        target_episode_id=None,
        target_source_key=None,
        target_title=None,
        target_episode_number=None,
        proposed_relationship="unresolved",
        confidence_score=0,
        confidence_class="low",
        match_reasons=["no_deterministic_target"],
    )
    result = export_variant_review._export_rows(
        [candidate], tmp_path, datetime(2026, 8, 12, tzinfo=UTC)
    )
    assert result["stats"]["unresolved"] == 1
