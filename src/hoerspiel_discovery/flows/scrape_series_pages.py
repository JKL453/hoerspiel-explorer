from prefect import flow

from hoerspiel_discovery.tasks.fetch import fetch_series_page
from hoerspiel_discovery.tasks.db_updates import (
    update_scrape_target_status,
    get_pending_targets,
)


@flow(name="scrape-hoerspiele-de-series-pages")
def scrape_hoerspiele_de():
    targets = get_pending_targets()
    print(f"Found {len(targets)} targets to scrape.")

    for target_id in targets:
        try:
            result = fetch_series_page(target_id)
            update_scrape_target_status(result)
        except Exception as e:
            update_scrape_target_status(
                {"external_id": target_id, "status": "error", "html_path": None},
                error=str(e),
            )


if __name__ == "__main__":
    scrape_hoerspiele_de()