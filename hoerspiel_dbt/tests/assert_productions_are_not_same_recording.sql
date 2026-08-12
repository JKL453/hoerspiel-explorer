select candidate_id
from {{ ref('episode_variant_candidates') }}
where variant_category in ('film_adaptation', 'live_production', 'other_production')
  and proposed_relationship = 'same_recording'
