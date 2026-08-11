select
    facts.episode_id,
    facts.release_year,
    speakers.speaker_id,
    speakers.speaker_name,
    roles.role_id,
    roles.role_name,
    concat(facts.episode_id, ':', speakers.speaker_id, ':', roles.role_id) as credit_key
from {{ ref('stg_episode_speakers') }} credits
join {{ ref('mart_episode_facts') }} facts using (episode_id)
join {{ ref('stg_speakers') }} speakers using (speaker_id)
join {{ ref('stg_roles') }} roles using (role_id)
