with ranked as (
    select
        features.*,
        row_number() over (
            partition by series_id, production_line_key, episode_number
            order by
                case when release_date is null then 1 else 0 end,
                release_date,
                case when cast_count > 0 then 0 else 1 end,
                episode_id
        ) as reference_rank
    from {{ ref('int_episode_variant_features') }} features
    where base_category = 'regular_candidate'
      and episode_number > 0
      and comparison_title <> ''
)

select
    concat(series_id, ':', production_line_key, ':', episode_number)
        as series_episode_number_key,
    series_id,
    series_name,
    production_line_key,
    production_line_label,
    production_line_order,
    episode_id,
    source_key,
    episode_number,
    episode_title,
    description,
    comparison_title,
    release_date,
    duration_minutes,
    order_number,
    cast_count,
    cast_fingerprint
from ranked
where reference_rank = 1
