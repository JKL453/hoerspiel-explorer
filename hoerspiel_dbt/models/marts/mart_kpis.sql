select
    count(*)::bigint as episode_count,
    count(distinct series_id)::bigint as series_count,
    count(distinct label_name)::bigint as label_count,
    count(distinct franchise_name)::bigint as franchise_count,
    count(*) filter (where release_year is null)::bigint as episodes_without_year,
    count(*) filter (where duration_minutes is null)::bigint as episodes_without_duration
from {{ ref('mart_episode_facts') }}
