from pathlib import Path
import re

from prefect import task

from hoerspiel_discovery.tasks.fetch import DETAIL_PAGES_DIR, SERIES_PAGES_DIR

REPLACEMENT_CHARACTER = "\ufffd"


def _contains_replacement_character(path: Path) -> bool:
    return REPLACEMENT_CHARACTER in path.read_text(encoding="utf-8")


def _episode_code_from_filename(path: Path) -> int | None:
    match = re.search(r"_code_(\d+)_", path.name)
    return int(match.group(1)) if match else None


@task(log_prints=True)
def find_pages_with_broken_encoding() -> dict[str, list[int]]:
    series_ids = []
    for path in sorted(SERIES_PAGES_DIR.glob("*.html")):
        if _contains_replacement_character(path):
            try:
                series_ids.append(int(path.stem))
            except ValueError:
                print(f"Cannot derive series ID from {path}; skipping.")

    episode_codes = []
    for path in sorted(DETAIL_PAGES_DIR.glob("*.html")):
        if not _contains_replacement_character(path):
            continue
        episode_code = _episode_code_from_filename(path)
        if episode_code is None:
            print(f"Cannot derive episode code from {path}; skipping.")
            continue
        episode_codes.append(episode_code)

    print(
        "Encoding scan completed: "
        f"{len(series_ids)} series pages and "
        f"{len(episode_codes)} detail pages require refetching."
    )
    return {"series_ids": series_ids, "episode_codes": episode_codes}
