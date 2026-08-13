select
    series_id,
    series_name,
    max(label_name) as label_name,
    franchise_name,
    production_line_key,
    production_line_label,
    production_line_order,
    category_key,
    category_label,
    category_order,
    concat(series_id, ':', production_line_key, ':', category_key)
        as series_category_key,
    count(*)::bigint as episode_count
from {{ ref('mart_series_episode_catalog') }}
group by
    series_id,
    series_name,
    franchise_name,
    production_line_key,
    production_line_label,
    production_line_order,
    category_key,
    category_label,
    category_order
