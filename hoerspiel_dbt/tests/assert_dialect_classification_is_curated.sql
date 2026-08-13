with dialect as (
    select catalog.episode_id, catalog.episode_number
    from {{ ref('mart_series_episode_catalog') }} catalog
    where catalog.series_name = 'Die Drei ???'
      and catalog.category_key = 'dialect'
)

select episode_id
from dialect
where episode_number not between 1 and 8

union all

select null::bigint
where (select count(*) from dialect) <> 8
