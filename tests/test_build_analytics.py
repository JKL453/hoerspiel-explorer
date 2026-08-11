import json

import pytest

from hoerspiel_discovery.tasks import build_analytics


def test_environment_validation_lists_missing_values(monkeypatch):
    for name in build_analytics.REQUIRED_DBT_ENV:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeError, match="DBT_HOST, DBT_USER, DBT_PASSWORD"):
        build_analytics._validate_environment()


def test_dbt_command_uses_project_profile_and_target(tmp_path):
    command = build_analytics._dbt_command("build", target_path=tmp_path)
    assert command[:2] == ["dbt", "build"]
    assert command[command.index("--project-dir") + 1] == str(
        build_analytics.DBT_PROJECT_DIR
    )
    assert command[command.index("--profiles-dir") + 1] == str(
        build_analytics.DBT_PROJECT_DIR
    )
    assert command[command.index("--target-path") + 1] == str(tmp_path)


def test_result_summary_counts_statuses(tmp_path):
    payload = {"results": [{"status": "success"}, {"status": "pass"}]}
    (tmp_path / "run_results.json").write_text(json.dumps(payload), encoding="utf-8")
    assert build_analytics._result_summary(tmp_path) == {"success": 1, "pass": 1}


def test_docs_are_only_replaced_when_complete(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "published"
    source.mkdir()
    destination.mkdir()
    (destination / "index.html").write_text("old", encoding="utf-8")

    with pytest.raises(RuntimeError, match="incomplete"):
        build_analytics._publish_docs(source, destination)
    assert (destination / "index.html").read_text(encoding="utf-8") == "old"

    for name in build_analytics.DOC_FILES:
        (source / name).write_text(f"new-{name}", encoding="utf-8")
    build_analytics._publish_docs(source, destination)
    assert sorted(path.name for path in destination.iterdir()) == sorted(
        build_analytics.DOC_FILES
    )
    assert (destination / "index.html").read_text(encoding="utf-8") == "new-index.html"
