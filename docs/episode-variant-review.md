# Episode variant review pilot

The first pilot analyzes only the main series `Die Drei ???`. It does not
merge, delete or update product records and does not affect the analytics
dashboard. The goal is to produce labeled examples before designing a
canonical work/production/publication schema.

## Model output

The dbt models tagged `episode_variant_pilot` classify every pilot record and
propose review links to deterministically selected regular episode references.
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

Review at least 50 rows across high, medium and low confidence. Fill only:

- `review_decision`: `accept`, `reject` or `uncertain`;
- `review_note`: a short explanation, especially for rejects and uncertain
  cases.

Do not change candidate IDs or source/target fields. Keep the reviewed CSV
outside the raw data directories. Importing decisions as a versioned dbt seed
is a separate future step.
