# Episode variant review pilot

The publication classifier now covers the complete catalog. The relationship
review remains limited to the main series `Die Drei ???`. Neither layer merges,
deletes or updates product records. The goal is to produce labeled examples
before designing a canonical work/production/publication schema.

## Model output

The dbt models tagged `episode_catalog` classify every publication. References
and relationship proposals are scoped to the same `series_id`; the Prefect
export then selects only the `Die Drei ???` pilot rows.
Explicit episode ranges have priority, followed by exact normalized titles.
Description, duration and cast fingerprints may strengthen a proposal, but
never create a link by themselves.

The relationship meanings are:

- `same_recording`: a format or reissue of the same recording;
- `contains`: a box, steelbook or compilation contains the target episode;
- `same_story_different_production`: the same story was produced again as a
  live, film, reading or other production;
- `unresolved`: no deterministic target was found.

Confidence is for review ordering only. No confidence class changes product
data automatically.

The curated dialect marker for `Die Drei ???` applies only to the eight Tudor
releases numbered 1 through 8. Leading ellipses alone are not a dialect signal.

## Generate a review file

1. Commit and deploy the dbt changes.
2. Run `build-dbt-analytics` and require all tests to pass.
3. Register the export deployment:

   ```bash
   prefect deploy --name export-episode-variant-review
   ```

4. Start `export-episode-variant-review` in Prefect.
5. Find the generated file and manifest below:

   ```text
   /data/hoerspiel-explorer/review/episode_variants/
   ├── die_drei_fragezeichen_<UTC timestamp>.csv
   └── latest.json
   ```

Every run creates a new CSV. Existing review files are never overwritten.
`latest.json` is updated atomically and points to the newest successful export.

## Review instructions

The first completed pilot is stored as the versioned dbt seed
`hoerspiel_dbt/seeds/episode_variant_reviews.csv`. For later review files, fill:

- `review_decision`: `accept`, `reject` or `uncertain`;
- `reviewed_category`: optional corrected category;
- `reviewed_markers`: optional corrected comma-separated markers;
- `review_note`: a short explanation, especially for rejects and uncertain
  cases.

Do not change candidate IDs or source/target fields. Keep working copies outside
the raw data directories. The versioned seed is the durable source for accepted
overrides; regenerated proposals remain distinguishable from human decisions.
