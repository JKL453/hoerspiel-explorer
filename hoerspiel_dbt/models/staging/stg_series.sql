select
    id::bigint as series_id,
    nullif(btrim(name), '') as series_name,
    nullif(nullif(btrim(label), ''), '?') as label_name,
    lower(regexp_replace(btrim(name), '\\s+', ' ', 'g')) as normalized_series_name
from {{ source('hoerspiel', 'series') }}
