select 1
from {{ ref('mart_kpis') }} kpis
where kpis.episode_count <> (select count(*) from {{ ref('mart_episode_facts') }})
   or kpis.series_count <> (select count(distinct series_id) from {{ ref('mart_episode_facts') }})
