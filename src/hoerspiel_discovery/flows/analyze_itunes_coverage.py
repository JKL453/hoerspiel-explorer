from prefect import flow

from hoerspiel_discovery.tasks.analyze_itunes import analyze_itunes_catalog_coverage


@flow(name="analyze-itunes-coverage", log_prints=True)
def analyze_itunes_coverage() -> dict:
    result = analyze_itunes_catalog_coverage()
    print(f"iTunes coverage pilot completed: {result}")
    return result


if __name__ == "__main__":
    analyze_itunes_coverage()
