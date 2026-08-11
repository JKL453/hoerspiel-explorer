# dbt analytics runbook

The analytics refresh is intentionally separate from the relational full
refresh. It reads product data but never truncates or rewrites the seven
product tables.

## One-time setup

1. Add the PostgreSQL connection values to the private Prefect worker
   environment managed by Ansible: `DBT_HOST`, `DBT_PORT`, `DBT_USER`,
   `DBT_PASSWORD`, `DBT_DBNAME`, and `DBT_SSLMODE=require`.
2. Prefer the Supabase Session Pooler when the direct database host is not
   reachable from the NUC. Never commit these values to this repository.
3. Deploy the flow:

   ```bash
   prefect deploy --name build-dbt-analytics
   ```

## First analytics release

1. Start `build-dbt-analytics` in Prefect and require successful `debug`,
   `seed`, `build`, tests, and docs generation.
2. In the Supabase SQL Editor, execute
   `src/hoerspiel_discovery/sql/06_analytics_functions.sql`. This is done after
   the first dbt build because the functions reference the new marts.
3. Test each `get_analytics_*` function in the SQL Editor and open the frontend
   statistics page.
4. Keep the old `get_episodes_per_year`, `get_top_genres`, and
   `get_top_labels` functions until the new dashboard has been accepted.

## Regular refresh

1. Complete and validate `load-cleaned-details` when a relational refresh is
   needed.
2. Start `build-dbt-analytics` separately.
3. Confirm Prefect reports no dbt errors and that the documentation artifacts
   exist below `/data/hoerspiel-explorer/dbt_docs`.
4. Check the dashboard totals and a sample of year, genre, speaker, and
   franchise results.

If dbt fails, the product tables and the last published docs remain available.
Fix the model, credentials, or source data and rerun the analytics deployment;
no relational reload is required.
