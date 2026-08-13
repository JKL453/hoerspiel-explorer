select source_key
from {{ ref('episode_variant_reviews') }}
where review_decision = 'accept'
  and (nullif(reviewed_category, '') is not null
    or nullif(reviewed_markers, '') is not null)
group by source_key
having count(distinct nullif(reviewed_category, '')) > 1
    or count(distinct nullif(reviewed_markers, '')) > 1
