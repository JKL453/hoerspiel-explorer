from prefect import flow

from hoerspiel_discovery.tasks.load_details import (
    assert_empty_destination,
    load_dimensions,
    load_episodes_and_relationships,
    preflight_cleaned_details,
    validate_loaded_database,
)


@flow(name="load-cleaned-details", log_prints=True)
def load_cleaned_details():
    preflight = preflight_cleaned_details()
    empty_destination = assert_empty_destination(preflight)
    dimensions_loaded = load_dimensions(empty_destination)
    episodes_loaded = load_episodes_and_relationships(dimensions_loaded)
    result = validate_loaded_database(episodes_loaded)
    print(f"Full refresh load completed successfully: {result['actual']}")
    return result


if __name__ == "__main__":
    load_cleaned_details()
