select id::bigint as genre_id, nullif(btrim(name), '') as genre_name
from {{ source('hoerspiel', 'genres') }}
