select
    features.episode_id,
    features.source_key,
    features.episode_number,
    features.episode_title,
    features.description,
    features.duration_minutes,
    features.release_date,
    features.order_number,
    features.cast_count,
    features.cast_fingerprint,
    case
        when reference_episodes.episode_id is not null then 'regular_episode'
        when features.base_category = 'regular_candidate' then 'unknown'
        else features.base_category
    end as variant_category,
    features.range_start,
    features.range_end,
    features.edition_markers,
    features.comparison_title
from {{ ref('int_episode_variant_features') }} features
left join {{ ref('int_regular_episode_references') }} reference_episodes
    on features.episode_id = reference_episodes.episode_id
