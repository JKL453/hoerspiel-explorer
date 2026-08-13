with catalog_counts as (
    select
        series_id,
        production_line_key,
        category_key,
        count(*)::bigint as episode_count
    from {{ ref('mart_series_episode_catalog') }}
    group by series_id, production_line_key, category_key
)

select
    coalesce(catalog.series_id, counts.series_id) as series_id,
    coalesce(
        catalog.production_line_key,
        counts.production_line_key
    ) as production_line_key,
    coalesce(catalog.category_key, counts.category_key) as category_key
from catalog_counts catalog
full outer join {{ ref('mart_series_category_counts') }} counts
    using (series_id, production_line_key, category_key, episode_count)
where catalog.series_id is null
   or counts.series_id is null
