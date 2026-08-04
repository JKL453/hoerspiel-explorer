from prefect import flow

from hoerspiel_discovery.tasks.parse import parse_series_page
from hoerspiel_discovery.tasks.db_updates import get_scraped_series


@flow(name="parse-series-pages")
def parse_all_series_pages():
    series = get_scraped_series()
    print(f"Found {len(series)} scraped series pages to parse.")

    total_episodes = 0
    for entry in series:
        count = parse_series_page(entry["external_id"], entry["html_path"])
        total_episodes += count

    print(f"Done. {total_episodes} episode targets added.")


if __name__ == "__main__":
    parse_all_series_pages()