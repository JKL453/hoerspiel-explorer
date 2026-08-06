from prefect import flow

from hoerspiel_discovery.tasks.build_details import (
    normalize_details,
    parse_and_clean_details,
    validate_and_publish_details,
)


@flow(name="build-cleaned-details", log_prints=True)
def build_cleaned_details():
    staging_result = parse_and_clean_details()
    candidate_result = normalize_details(staging_result)
    result = validate_and_publish_details(candidate_result)

    validation = result["validation"]
    parse_stats = result["parse_stats"]
    print(
        "Build completed: "
        f"{validation['records']} records published, "
        f"{validation['stubs']} stubs, "
        f"{len(parse_stats['parse_errors'])} parse errors."
    )
    return result


if __name__ == "__main__":
    build_cleaned_details()
