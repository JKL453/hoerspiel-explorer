import json
from types import SimpleNamespace

import pytest

from hoerspiel_discovery.tasks import build_details, load_details


class FakeQuery:
    def __init__(self, client, table):
        self.client = client
        self.table = table
        self.operation = "select"
        self.rows = []
        self.columns = "*"
        self.count_requested = False
        self.range_value = None
        self.limit_value = None
        self.filters = []
        self.conflict = ""

    def select(self, columns, count=None, **kwargs):
        self.operation = "select"
        self.columns = columns
        self.count_requested = count == "exact"
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def range(self, start, end):
        self.range_value = (start, end)
        return self

    def in_(self, column, values):
        self.filters.append((column, set(values)))
        return self

    def upsert(self, rows, on_conflict):
        self.operation = "upsert"
        self.rows = [row.copy() for row in rows]
        self.conflict = on_conflict
        return self

    def execute(self):
        table_rows = self.client.tables[self.table]
        if self.operation == "upsert":
            conflict_columns = self.conflict.split(",")
            for incoming in self.rows:
                existing = next(
                    (
                        row
                        for row in table_rows
                        if all(row.get(key) == incoming.get(key) for key in conflict_columns)
                    ),
                    None,
                )
                if existing:
                    existing.update(incoming)
                else:
                    row = incoming.copy()
                    if self.table in {
                        "series",
                        "genres",
                        "speakers",
                        "roles",
                        "episodes",
                    }:
                        row["id"] = len(table_rows) + 1
                    table_rows.append(row)
            return SimpleNamespace(data=self.rows, count=None)

        rows = list(table_rows)
        for column, values in self.filters:
            rows = [row for row in rows if row.get(column) in values]
        total = len(rows)
        if self.range_value:
            start, end = self.range_value
            rows = rows[start : end + 1]
        if self.limit_value is not None:
            rows = rows[: self.limit_value]
        if self.columns != "*":
            columns = [column.strip() for column in self.columns.split(",")]
            rows = [{column: row[column] for column in columns} for row in rows]
        return SimpleNamespace(
            data=rows,
            count=total if self.count_requested else None,
        )


class FakeClient:
    def __init__(self):
        self.tables = {table: [] for table in load_details.PRODUCT_TABLES}

    def table(self, name):
        return FakeQuery(self, name)


def _record(source_url="https://www.hoerspiele.de/hsp_anzeige.asp?code=42"):
    record = {
        "title": "Episode",
        "series_name": "Series",
        "episode_number": 1,
        "description": "Description",
        "duration_minutes": 42.0,
        "release_date": "01.02.2020",
        "label": "Label",
        "cover_url": None,
        "speakers": [{"speaker": "Actor", "role": "Hero"}],
        "order_number": None,
        "genres": ["Adventure"],
        "previous_episode_url": None,
        "next_episode_url": None,
        "source_url": source_url,
    }
    record["source_key"] = build_details._build_source_key(record)
    return record


def test_preflight_rejects_invalid_date_and_duplicate_key():
    record = _record()
    invalid_date = record.copy()
    invalid_date["source_key"] = "other"
    invalid_date["source_url"] = "https://example.test/other"
    invalid_date["release_date"] = "2020-01-01"
    with pytest.raises(ValueError, match="invalid release dates"):
        load_details._build_manifest([record, invalid_date])

    with pytest.raises(ValueError, match="duplicate source_key"):
        load_details._build_manifest([record, record.copy()])


def test_series_dimension_prefers_non_null_label():
    first = _record()
    first["label"] = None
    second = _record("https://www.hoerspiele.de/hsp_anzeige.asp?code=43")

    dimensions = load_details._collect_dimensions([first, second])

    assert dimensions["series"] == [{"name": "Series", "label": "Label"}]


def test_empty_destination_guard_rejects_existing_rows(monkeypatch):
    client = FakeClient()
    client.tables["episodes"].append({"id": 1})
    monkeypatch.setattr(load_details, "get_client", lambda: client)

    with pytest.raises(RuntimeError, match="not empty"):
        load_details.assert_empty_destination.fn({"manifest": {}})


def test_full_loader_tasks_and_post_load_counts(monkeypatch, tmp_path):
    linked = _record()
    stub = _record(None)
    stub.update(
        {
            "title": "Stub",
            "episode_number": 2,
            "description": None,
            "duration_minutes": None,
            "release_date": None,
            "label": None,
            "speakers": [],
            "genres": [],
        }
    )
    stub["source_key"] = build_details._build_source_key(stub)
    records = [linked, stub]
    path = tmp_path / "cleaned_details.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    preflight = {"path": str(path), "manifest": load_details._build_manifest(records)}
    client = FakeClient()
    monkeypatch.setattr(load_details, "get_client", lambda: client)

    checked = load_details.assert_empty_destination.fn(preflight)
    dimensions = load_details.load_dimensions.fn(checked)
    episodes = load_details.load_episodes_and_relationships.fn(dimensions)
    result = load_details.validate_loaded_database.fn(episodes)

    assert result["actual"] == {
        table: preflight["manifest"][table] for table in load_details.PRODUCT_TABLES
    }
    assert len(client.tables["episodes"]) == 2
    assert client.tables["episodes"][1]["source_key"].startswith(
        "hoerspiele.de:stub:"
    )
