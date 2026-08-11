select
    release_year as year,
    genre_name,
    count(distinct episode_id)::bigint as episode_count,
    concat(release_year, ':', genre_name) as year_genre_key
from {{ ref('mart_episode_genres') }}
where release_year is not null
group by release_year, genre_name
