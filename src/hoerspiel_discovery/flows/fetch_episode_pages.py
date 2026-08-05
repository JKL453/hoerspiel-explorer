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

    for i, target in enumerate(targets, start=1):
        episode_code = target["episode_code"]
        try:
            result = fetch_episode_page(episode_code, target["attempts"])
            update_episode_target_status(result)
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

        if i % 100 == 0:
            print(f"Progress: {i}/{len(targets)} episode pages processed.")

    print(f"Done. {len(targets)} episode targets processed.")


if __name__ == "__main__":
    fetch_all_episode_pages()
