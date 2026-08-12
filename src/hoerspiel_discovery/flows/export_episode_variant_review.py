from prefect import flow

from hoerspiel_discovery.tasks.export_variant_review import (
    export_episode_variant_review_csv,
)


@flow(name="export-episode-variant-review", log_prints=True)
def export_episode_variant_review():
    result = export_episode_variant_review_csv()
    print(
        "Episode variant review export completed: "
        f"{result['stats']['records']} candidates written to {result['csv_path']}"
    )
    return result


if __name__ == "__main__":
    export_episode_variant_review()
