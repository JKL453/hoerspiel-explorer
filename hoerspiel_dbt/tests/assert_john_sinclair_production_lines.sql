select episode_id
from {{ ref('mart_series_episode_catalog') }}
where series_name = 'John Sinclair'
  and (
    (lower(coalesce(label_name, '')) ~ '(tonstudio braun|^tsb)'
      and production_line_key <> 'tonstudio_braun')
    or
    (lower(coalesce(label_name, '')) !~ '(tonstudio braun|^tsb)'
      and production_line_key <> 'edition_2000')
  )
