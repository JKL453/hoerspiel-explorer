select facts.episode_id
from {{ ref('mart_episode_facts') }} facts
left join {{ ref('mart_series_episode_catalog') }} catalog using (episode_id)
where catalog.episode_id is null

union all

select catalog.episode_id
from {{ ref('mart_series_episode_catalog') }} catalog
left join {{ ref('mart_episode_facts') }} facts using (episode_id)
where facts.episode_id is null
