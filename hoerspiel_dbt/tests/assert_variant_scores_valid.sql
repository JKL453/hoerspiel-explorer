select candidate_id
from {{ ref('episode_variant_candidates') }}
where confidence_score < 0
   or confidence_score > 100
   or (confidence_score >= 90 and confidence_class <> 'high')
   or (confidence_score between 70 and 89 and confidence_class <> 'medium')
   or (confidence_score < 70 and confidence_class <> 'low')
