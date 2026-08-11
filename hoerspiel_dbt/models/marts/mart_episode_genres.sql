select
    facts.episode_id,
    facts.release_year,
    genres.genre_id,
    genres.genre_name,
    concat(facts.episode_id, ':', genres.genre_id) as episode_genre_key
from {{ ref('stg_episode_genres') }} links
join {{ ref('mart_episode_facts') }} facts using (episode_id)
join {{ ref('stg_genres') }} genres using (genre_id)
