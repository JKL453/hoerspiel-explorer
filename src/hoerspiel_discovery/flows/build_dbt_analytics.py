from prefect import flow

from hoerspiel_discovery.tasks.build_analytics import (
    build_dbt_models,
    debug_dbt_connection,
    generate_and_publish_dbt_docs,
    seed_dbt,
)


@flow(name="build-dbt-analytics", log_prints=True)
def build_dbt_analytics():
    debug_dbt_connection()
    seed_dbt()
    build_summary = build_dbt_models()
    result = generate_and_publish_dbt_docs(build_summary)
    print(f"Analytics build completed successfully: {result}")
    return result


if __name__ == "__main__":
    build_dbt_analytics()
