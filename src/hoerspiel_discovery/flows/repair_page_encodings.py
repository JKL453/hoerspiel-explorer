import time

from prefect import flow

from hoerspiel_discovery.tasks.fetch import fetch_episode_page, fetch_series_page
from hoerspiel_discovery.tasks.repair_encoding import find_pages_with_broken_encoding


@flow(name="repair-page-encodings", log_prints=True)
def repair_page_encodings():
    corrupted = find_pages_with_broken_encoding()
    series_ids = corrupted["series_ids"]
    episode_codes = corrupted["episode_codes"]
    errors = []

    for index, series_id in enumerate(series_ids, start=1):
        print(f"Series repair: {index}/{len(series_ids)} (ID {series_id}).")
        try:
            time.sleep(3.0)
            fetch_series_page(series_id)
        except Exception as exc:
            errors.append(f"series {series_id}: {exc}")
            print(f"Series {series_id} repair failed: {exc}")

    for index, episode_code in enumerate(episode_codes, start=1):
        print(
            f"Detail repair: {index}/{len(episode_codes)} "
            f"(code {episode_code})."
        )
        try:
            fetch_episode_page(episode_code, attempts=0)
        except Exception as exc:
            errors.append(f"episode {episode_code}: {exc}")
            print(f"Episode {episode_code} repair failed: {exc}")

    if errors:
        preview = "; ".join(errors[:10])
        raise RuntimeError(f"Encoding repair failed for {len(errors)} pages: {preview}")

    remaining = find_pages_with_broken_encoding()
    remaining_count = len(remaining["series_ids"]) + len(remaining["episode_codes"])
    if remaining_count:
        raise RuntimeError(
            f"Encoding repair validation found {remaining_count} corrupted pages."
        )

    print(
        "Encoding repair completed: "
        f"{len(series_ids)} series pages and "
        f"{len(episode_codes)} detail pages replaced."
    )
    return {
        "series_pages_repaired": len(series_ids),
        "detail_pages_repaired": len(episode_codes),
    }


if __name__ == "__main__":
    repair_page_encodings()
