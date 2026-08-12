with fanbox as (
    select episode_id
    from {{ ref('episode_variant_classifications') }}
    where lower(episode_title) like 'fanbox (folgen 01-%03)%'
    limit 1
),
actual as (
    select
        count(*)::integer as link_count,
        min(target_episode_number)::integer as first_episode,
        max(target_episode_number)::integer as last_episode
    from {{ ref('episode_variant_candidates') }}
    where source_episode_id = (select episode_id from fanbox)
      and proposed_relationship = 'contains'
)
select *
from actual
where link_count <> 3
   or first_episode <> 1
   or last_episode <> 3
