select episode_id
from {{ ref('episode_variant_classifications') }}
where series_name = 'John Sinclair'
  and lower(episode_title) ~ '(teil\s*)?[0-9]+\s*/\s*[0-9]+'
  and variant_category in ('box_set', 'compilation')
  and edition_markers not like '%container%'
  and edition_markers not like '%compilation%'
