import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from prefect import get_run_logger, task

from hoerspiel_discovery.config import BASE_DIR, DBT_DOCS_DIR


DBT_PROJECT_DIR = BASE_DIR / "hoerspiel_dbt"
REQUIRED_DBT_ENV = ("DBT_HOST", "DBT_USER", "DBT_PASSWORD")
DOC_FILES = ("index.html", "manifest.json", "catalog.json")


def _validate_environment() -> None:
    missing = [name for name in REQUIRED_DBT_ENV if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing dbt environment variables: {', '.join(missing)}")


def _dbt_command(*arguments: str, target_path: Path | None = None) -> list[str]:
    command = [
        "dbt",
        *arguments,
        "--project-dir",
        str(DBT_PROJECT_DIR),
        "--profiles-dir",
        str(DBT_PROJECT_DIR),
    ]
    if target_path is not None:
        command.extend(("--target-path", str(target_path)))
    return command


def _run_command(command: list[str]) -> None:
    logger = get_run_logger()
    logger.info("Running: %s", " ".join(command[:2]))
    process = subprocess.Popen(
        command,
        cwd=DBT_PROJECT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )
    assert process.stdout is not None
    for line in process.stdout:
        logger.info(line.rstrip())
    return_code = process.wait()
    if return_code:
        raise RuntimeError(
            f"dbt command {command[1]!r} failed with exit code {return_code}"
        )


def _result_summary(target_path: Path) -> dict[str, int]:
    run_results_path = target_path / "run_results.json"
    if not run_results_path.exists():
        return {}
    payload = json.loads(run_results_path.read_text(encoding="utf-8"))
    summary: dict[str, int] = {}
    for result in payload.get("results", []):
        status = str(result.get("status", "unknown"))
        summary[status] = summary.get(status, 0) + 1
    return summary


def _publish_docs(source: Path, destination: Path) -> None:
    missing = [name for name in DOC_FILES if not (source / name).is_file()]
    if missing:
        raise RuntimeError(f"dbt docs output is incomplete: {', '.join(missing)}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent)
    )
    backup = destination.with_name(f".{destination.name}-previous")
    try:
        for name in DOC_FILES:
            shutil.copy2(source / name, staging / name)
        if backup.exists():
            shutil.rmtree(backup)
        if destination.exists():
            destination.rename(backup)
        staging.rename(destination)
        if backup.exists():
            shutil.rmtree(backup)
    except Exception:
        if not destination.exists() and backup.exists():
            backup.rename(destination)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)


@task(name="dbt-debug")
def debug_dbt_connection() -> None:
    _validate_environment()
    _run_command(_dbt_command("debug"))


@task(name="dbt-seed")
def seed_dbt() -> None:
    _run_command(_dbt_command("seed"))


@task(name="dbt-build")
def build_dbt_models() -> dict[str, int]:
    with tempfile.TemporaryDirectory(prefix="hoerspiel-dbt-build-") as directory:
        target_path = Path(directory)
        _run_command(
            _dbt_command(
                "build", "--exclude", "resource_type:seed", target_path=target_path
            )
        )
        summary = _result_summary(target_path)
    get_run_logger().info("dbt build result: %s", summary)
    return summary


@task(name="dbt-docs")
def generate_and_publish_dbt_docs(build_summary: dict[str, int]) -> dict:
    with tempfile.TemporaryDirectory(prefix="hoerspiel-dbt-docs-") as directory:
        target_path = Path(directory)
        _run_command(_dbt_command("docs", "generate", target_path=target_path))
        _publish_docs(target_path, DBT_DOCS_DIR)
    result = {"build": build_summary, "docs_path": str(DBT_DOCS_DIR)}
    get_run_logger().info("Published dbt docs to %s", DBT_DOCS_DIR)
    return result
