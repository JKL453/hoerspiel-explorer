select episode_id::bigint as episode_id, genre_id::bigint as genre_id
from {{ source('hoerspiel', 'episode_genres') }}
