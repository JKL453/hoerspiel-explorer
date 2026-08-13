select candidates.candidate_id
from {{ ref('episode_variant_candidates') }} candidates
join {{ ref('mart_episode_facts') }} source
  on source.episode_id = candidates.source_episode_id
join {{ ref('mart_episode_facts') }} target
  on target.episode_id = candidates.target_episode_id
join {{ ref('episode_variant_classifications') }} source_classification
  on source_classification.episode_id = candidates.source_episode_id
join {{ ref('episode_variant_classifications') }} target_classification
  on target_classification.episode_id = candidates.target_episode_id
where candidates.target_episode_id is not null
  and (
    source.series_id <> target.series_id
    or source_classification.production_line_key
       <> target_classification.production_line_key
  )
