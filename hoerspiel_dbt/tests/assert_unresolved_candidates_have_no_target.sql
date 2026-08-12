select candidate_id
from {{ ref('episode_variant_candidates') }}
where (proposed_relationship = 'unresolved' and target_episode_id is not null)
   or (proposed_relationship <> 'unresolved' and target_episode_id is null)
