select genre_name, count(distinct episode_id)::bigint as episode_count
from {{ ref('mart_episode_genres') }}
group by genre_name
