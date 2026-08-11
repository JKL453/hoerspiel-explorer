select release_year as year, count(*)::bigint as episode_count
from {{ ref('mart_episode_facts') }}
where release_year is not null
group by release_year
