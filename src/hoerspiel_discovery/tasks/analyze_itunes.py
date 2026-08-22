from prefect import get_run_logger, task

from hoerspiel_discovery.config import ITUNES_COVERAGE_DIR
from hoerspiel_discovery.enrichment.itunes_coverage import (
    ItunesSearchClient,
    build_coverage_report,
    publish_report,
)


@task(name="analyze-itunes-catalog-coverage", log_prints=True)
def analyze_itunes_catalog_coverage() -> dict:
    logger = get_run_logger()
    report = build_coverage_report(
        ItunesSearchClient(),
        progress=lambda message: logger.info(message),
    )
    report_path = publish_report(report, ITUNES_COVERAGE_DIR)
    summary = report["summary"]
    logger.info(
        "Coverage complete: %s candidates, %s distinct numbered episodes; "
        "%s queries reached the API limit.",
        summary["candidate_results"],
        summary["distinct_numbered_episodes"],
        summary["limit_reached_queries"],
    )
    return {"report_path": str(report_path), "summary": summary}
