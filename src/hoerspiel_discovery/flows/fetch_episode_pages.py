from prefect import flow

from hoerspiel_discovery.tasks.db_updates import (
    get_pending_episode_targets,
    update_episode_target_status,
)
from hoerspiel_discovery.tasks.fetch import fetch_episode_page


@flow(name="fetch-episode-pages")
def fetch_all_episode_pages(limit: int | None = None):
    targets = get_pending_episode_targets()
    if limit is not None:
        targets = targets[:limit]
    print(f"Found {len(targets)} episode targets to scrape.")

    counts = {"success": 0, "not_found": 0, "error": 0}

    for i, target in enumerate(targets, start=1):
        episode_code = target["episode_code"]
        print(
            f"[{i}/{len(targets)}] Processing episode {episode_code} "
            f"(previous attempts: {target['attempts']})."
        )
        try:
            result = fetch_episode_page(episode_code, target["attempts"])
            update_episode_target_status(result)
            counts[result["status"]] += 1
            print(
                f"[{i}/{len(targets)}] Episode {episode_code}: "
                f"{result['status']}."
            )
        except Exception as e:
            update_episode_target_status(
                {
                    "episode_code": episode_code,
                    "attempts": target["attempts"],
                    "status": "error",
                    "html_path": None,
                },
                error=str(e),
            )
            counts["error"] += 1
            print(f"[{i}/{len(targets)}] Episode {episode_code}: error: {e}")

        if i % 10 == 0 or i == len(targets):
            print(
                f"Progress: {i}/{len(targets)} processed "
                f"(success={counts['success']}, "
                f"not_found={counts['not_found']}, error={counts['error']})."
            )

    print(
        f"Done. {len(targets)} processed "
        f"(success={counts['success']}, "
        f"not_found={counts['not_found']}, error={counts['error']})."
    )


if __name__ == "__main__":
    fetch_all_episode_pages()
