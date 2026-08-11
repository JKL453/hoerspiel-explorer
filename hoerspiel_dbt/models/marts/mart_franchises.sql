select
    franchise_name,
    count(distinct series_id)::bigint as series_count,
    count(*)::bigint as episode_count
from {{ ref('mart_episode_facts') }}
group by franchise_name
