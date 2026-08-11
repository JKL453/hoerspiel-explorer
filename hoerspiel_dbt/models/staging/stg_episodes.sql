select
    id::bigint as episode_id,
    series_id::bigint as series_id,
    nullif(btrim(source_key), '') as source_key,
    episode_number::bigint as episode_number,
    nullif(btrim(title), '') as episode_title,
    nullif(btrim(description), '') as description,
    duration_minutes::double precision as duration_minutes,
    release_date::date as release_date,
    extract(year from release_date)::integer as release_year,
    nullif(btrim(cover_url), '') as cover_url,
    nullif(btrim(order_number), '') as order_number,
    nullif(btrim(source_url), '') as source_url
from {{ source('hoerspiel', 'episodes') }}
