# Hörspiel Explorer pipeline

This diagram shows the current ingestion and processing pipeline. Rectangles
with a blue border are Prefect deployments. The database reset remains a
deliberate manual operation and is not part of a Prefect flow.

```mermaid
flowchart TD
    source[hoerspiele.de]

    subgraph discovery[Discovery and raw ingestion]
        seed[Seed scrape_targets]
        scrape["Prefect: scrape-hoerspiele-de-series-pages"]
        rawSeries[(raw/series_pages/*.html)]
        scrapeTargets[(Supabase: scrape_targets)]

        parseSeries["Prefect: parse-series-pages"]
        episodeTargets[(Supabase: episode_targets)]

        fetchEpisodes["Prefect: fetch-episode-pages"]
        rawDetails[(raw/detail_pages/*.html)]
    end

    subgraph repair[Conditional encoding repair]
        scan[Scan raw HTML for U+FFFD]
        repairFlow["Prefect: repair-page-encodings"]
        verifyRepair[Verify zero corrupted raw pages]
    end

    subgraph transform[Parse, clean, and validate]
        build["Prefect: build-cleaned-details"]
        parseClean[Parse pages, clean records, create stubs]
        staging[(cleaned_details_staging.json)]
        normalize[Deduplicate and normalize speakers/roles]
        candidate[(cleaned_details_candidate.json)]
        validate[Validate schema, source_key, and encoding]
        cleaned[(cleaned_details.json)]
    end

    subgraph refresh[Controlled relational refresh]
        manualReset["Manual SQL: TRUNCATE product tables"]
        sourceKey["Manual SQL: ensure episodes.source_key"]
        load["Prefect: load-cleaned-details"]
        preflight[Preflight JSON and require empty destination]
        dimensions[Load series, genres, speakers, and roles]
        episodes[Load episodes and junction tables]
        postcheck[Validate all relational counts]
        database[(Supabase product tables)]
    end

    subgraph downstream[Downstream processing]
        embeddings["Future Prefect flow: generate embeddings"]
        dbt[dbt staging and marts]
        frontend[Next.js analytics and RAG]
    end

    seed --> scrapeTargets
    scrapeTargets --> scrape
    source --> scrape
    scrape --> rawSeries
    scrape --> scrapeTargets

    rawSeries --> parseSeries
    parseSeries --> episodeTargets
    episodeTargets --> fetchEpisodes
    source --> fetchEpisodes
    fetchEpisodes --> rawDetails

    rawSeries -. corrupted characters .-> scan
    rawDetails -. corrupted characters .-> scan
    scan --> repairFlow
    source --> repairFlow
    repairFlow --> rawSeries
    repairFlow --> rawDetails
    repairFlow --> verifyRepair

    rawSeries --> build
    rawDetails --> build
    build --> parseClean --> staging --> normalize --> candidate --> validate --> cleaned

    manualReset --> sourceKey
    sourceKey --> load
    cleaned --> load
    load --> preflight --> dimensions --> episodes --> postcheck --> database

    database -. descriptions without embeddings .-> embeddings
    embeddings -. vectors .-> database
    database --> dbt --> frontend

    classDef prefect fill:#e8f1ff,stroke:#2563eb,stroke-width:2px,color:#111827;
    classDef manual fill:#fff1f2,stroke:#dc2626,stroke-width:2px,color:#111827;
    classDef future fill:#f3f4f6,stroke:#6b7280,stroke-dasharray:5 5,color:#374151;

    class scrape,parseSeries,fetchEpisodes,repairFlow,build,load prefect;
    class manualReset,sourceKey manual;
    class embeddings future;
```

## Operational order for a full refresh

1. Run the discovery flows until series and episode targets are complete.
2. Run `repair-page-encodings` only when the raw-page scan finds `U+FFFD`.
3. Run `build-cleaned-details` and require successful artifact validation.
4. Empty the seven product tables manually; keep target tables intact.
5. Run `load-cleaned-details` and require matching post-load counts.
6. Generate embeddings, then build dbt models and downstream views.

The loader never truncates tables. If it fails partway through an initial full
refresh, empty the product tables again before restarting it.
