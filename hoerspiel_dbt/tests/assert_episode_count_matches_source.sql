select 1
where
    (select count(*) from {{ ref('mart_episode_facts') }})
    <>
    (select count(*) from {{ source('hoerspiel', 'episodes') }})
