with catalog as (
    select *
    from {{ ref('mart_series_episode_catalog') }}
    where series_name = 'John Sinclair'
),
mappings as (
    select * from {{ ref('episode_production_line_mappings') }}
)

select catalog.episode_id
from catalog
left join mappings using (source_key)
where coalesce(mappings.production_line_key, 'edition_2000')
    <> catalog.production_line_key

union all

select null::bigint
where (
    select count(*)
    from catalog
    where production_line_key = 'tonstudio_braun'
) <> (select count(*) from mappings)
