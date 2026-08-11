select
    label_name,
    count(distinct series_id)::bigint as series_count,
    count(*)::bigint as episode_count
from {{ ref('mart_episode_facts') }}
where label_name is not null
group by label_name
