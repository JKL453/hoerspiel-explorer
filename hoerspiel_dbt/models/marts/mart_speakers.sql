select
    speaker_id,
    speaker_name,
    count(distinct episode_id)::bigint as episode_count,
    count(distinct role_id)::bigint as role_count,
    count(*)::bigint as credit_count
from {{ ref('mart_speaker_credits') }}
group by speaker_id, speaker_name
