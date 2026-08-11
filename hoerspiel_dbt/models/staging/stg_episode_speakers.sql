select episode_id::bigint as episode_id, speaker_id::bigint as speaker_id, role_id::bigint as role_id
from {{ source('hoerspiel', 'episode_speakers') }}
