select
    series_id,
    series_name,
    label_name,
    franchise_name,
    category_key,
    category_label,
    category_order,
    concat(series_id, ':', category_key) as series_category_key,
    count(*)::bigint as episode_count
from {{ ref('mart_series_episode_catalog') }}
group by
    series_id,
    series_name,
    label_name,
    franchise_name,
    category_key,
    category_label,
    category_order
