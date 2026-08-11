select episode_id, duration_minutes
from {{ ref('mart_episode_facts') }}
where duration_minutes < 0
