from prefect import flow

from hoerspiel_discovery.tasks.parse import parse_series_page
from hoerspiel_discovery.tasks.db_updates import get_scraped_series


@flow(name="parse-series-pages")
def parse_all_series_pages():
    series = get_scraped_series()
    print(f"Found {len(series)} scraped series pages to parse.")

    total_episodes = 0
    for i, entry in enumerate(series, start=1):
        count = parse_series_page(entry["external_id"], entry["html_path"])
        total_episodes += count
        if i % 100 == 0:
            print(f"Progress: {i}/{len(series)} series processed, {total_episodes} episodes so far.")

    print(f"Done. {total_episodes} episode targets added.")
