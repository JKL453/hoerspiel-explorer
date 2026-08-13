select source.episode_id
from {{ ref('mart_episode_facts') }} source
left join {{ ref('episode_variant_classifications') }} classified using (episode_id)
where classified.episode_id is null
