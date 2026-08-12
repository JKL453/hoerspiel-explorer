with sample as (
    select episode_id
    from {{ ref('episode_variant_classifications') }}
    where lower(episode_title) = 'und der superpapagei (lp-edition)'
),
actual as (
    select count(*)::integer as link_count
    from {{ ref('episode_variant_candidates') }} candidates
    where candidates.source_episode_id = (select episode_id from sample)
      and candidates.proposed_relationship = 'same_recording'
      and candidates.target_episode_number = 1
)
select * from actual where link_count <> 1
