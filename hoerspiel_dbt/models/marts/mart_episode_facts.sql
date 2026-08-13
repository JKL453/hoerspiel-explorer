with episodes as (
    select * from {{ ref('stg_episodes') }}
),
series as (
    select * from {{ ref('stg_series') }}
),
franchises as (
    select normalized_series_name, franchise_name
    from {{ ref('franchise_mappings') }}
)

select
    episodes.episode_id,
    episodes.source_key,
    episodes.series_id,
    series.series_name,
    series.label_name,
    coalesce(franchises.franchise_name, series.series_name) as franchise_name,
    episodes.episode_number,
    episodes.episode_title,
    episodes.description,
    episodes.release_date,
    episodes.release_year,
    episodes.duration_minutes,
    episodes.cover_url,
    episodes.order_number,
    episodes.source_url
from episodes
left join series using (series_id)
left join franchises using (normalized_series_name)
