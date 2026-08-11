select id::bigint as role_id, nullif(btrim(name), '') as role_name
from {{ source('hoerspiel', 'roles') }}
