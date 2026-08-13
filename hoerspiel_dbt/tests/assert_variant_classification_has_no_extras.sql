select classified.episode_id
from {{ ref('episode_variant_classifications') }} classified
left join {{ ref('mart_episode_facts') }} source using (episode_id)
where source.episode_id is null
