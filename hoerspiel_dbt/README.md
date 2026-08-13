# Hörspiel Explorer analytics

This dbt project turns the normalized Supabase tables in `public` into a
documented analytics layer in the separate `analytics` schema.

## Lineage

```mermaid
flowchart LR
    public[(public product tables)] --> staging[stg_* views]
    staging --> facts[episode, genre and speaker facts]
    seed[franchise_mappings seed] --> facts
    facts --> marts[aggregate marts]
    reviewSeed[episode_variant_reviews seed] --> profiling
    facts --> profiling[global publication classification]
    profiling --> catalog[series catalog marts]
    facts --> rpc[public analytics RPCs]
    marts --> tests[dbt data tests and docs]
    rpc --> dashboard[Next.js statistics dashboard]
    profiling --> review[Prefect Die Drei ??? relationship review]
    catalog --> catalogRpc[public catalog RPCs]
    catalogRpc --> seriesPages[Next.js series search and category tabs]
```

Staging models standardize names and types without changing source data. The
fact marts retain the grains needed for year filtering, while aggregate marts
provide inspectable all-time results and portfolio-friendly lineage.

## Local commands

Set `DBT_HOST`, `DBT_USER`, `DBT_PASSWORD`, and optionally `DBT_PORT`,
`DBT_DBNAME`, `DBT_SSLMODE`, and `DBT_THREADS`. Then run:

```bash
dbt debug --project-dir hoerspiel_dbt --profiles-dir hoerspiel_dbt
dbt seed --project-dir hoerspiel_dbt --profiles-dir hoerspiel_dbt
dbt build --exclude resource_type:seed --project-dir hoerspiel_dbt --profiles-dir hoerspiel_dbt
dbt docs generate --project-dir hoerspiel_dbt --profiles-dir hoerspiel_dbt
```

The production path is the Prefect deployment `build-dbt-analytics`. It logs
every dbt step and publishes complete documentation artifacts to
`/data/hoerspiel-explorer/dbt_docs` only after a successful build.

## Franchise curation

`seeds/franchise_mappings.csv` contains the initial mappings for the largest
recognizable franchises in the current dataset. Matching uses normalized,
case-folded series names. Every series without a mapping remains visible as its
own franchise, so the seed never drops or guesses away records.

## Categorized publication catalog

Models in `models/profiling` classify every source publication with global,
deterministic rules. References and relationship proposals are always scoped
to `series_id`, so identical episode numbers in different series can never be
linked. Accepted human overrides from `episode_variant_reviews.csv` take
precedence without changing product tables.

`mart_series_episode_catalog` translates the technical categories and markers
into stable user-facing groups. `mart_series_category_counts` supplies the
search overview and category navigation. The models are read-only and tagged
`episode_catalog`.

The relationship-review export remains deliberately limited to the `Die Drei
???` pilot. Operational and review instructions are documented in
[`docs/episode-variant-review.md`](../docs/episode-variant-review.md).
