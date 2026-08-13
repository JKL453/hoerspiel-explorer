with features as (
    select * from {{ ref('int_episode_variant_features') }}
),
reference_episodes as (
    select * from {{ ref('int_regular_episode_references') }}
),
review_overrides as (
    select
        source_key,
        max(nullif(reviewed_category, '')) as reviewed_category,
        max(nullif(reviewed_markers, '')) as reviewed_markers
    from {{ ref('episode_variant_reviews') }}
    where review_decision = 'accept'
      and (nullif(reviewed_category, '') is not null
        or nullif(reviewed_markers, '') is not null)
    group by source_key
),
machine_classifications as (
    select
        features.*,
        case
            when reference_episodes.episode_id is not null then 'regular_episode'
            when features.base_category = 'regular_candidate' then 'unknown'
            else features.base_category
        end as machine_category
    from features
    left join reference_episodes
        on features.episode_id = reference_episodes.episode_id
)

select
    machine.series_id,
    machine.series_name,
    machine.franchise_name,
    machine.episode_id,
    machine.source_key,
    machine.episode_number,
    machine.episode_title,
    machine.description,
    machine.duration_minutes,
    machine.release_date,
    machine.order_number,
    machine.cast_count,
    machine.cast_fingerprint,
    coalesce(review.reviewed_category, machine.machine_category) as variant_category,
    machine.machine_category,
    case when review.source_key is not null then 'reviewed' else 'machine' end
        as classification_source,
    machine.range_start,
    machine.range_end,
    coalesce(review.reviewed_markers, machine.edition_markers) as edition_markers,
    machine.comparison_title
from machine_classifications machine
left join review_overrides review using (source_key)
