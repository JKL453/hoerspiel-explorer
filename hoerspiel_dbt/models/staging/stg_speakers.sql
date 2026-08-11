select id::bigint as speaker_id, nullif(btrim(name), '') as speaker_name
from {{ source('hoerspiel', 'speakers') }}
