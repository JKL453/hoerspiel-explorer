with classifications as (
    select * from {{ ref('episode_variant_classifications') }}
),
reference_episodes as (
    select * from {{ ref('int_regular_episode_references') }}
),
range_matches as (
    select
        source.episode_id as source_episode_id,
        target.episode_id as target_episode_id,
        'contains'::text as proposed_relationship,
        100::integer as confidence_score,
        '["explicit_episode_range"]'::jsonb as match_reasons
    from classifications source
    join reference_episodes target
      on target.episode_number between source.range_start and source.range_end
    where source.variant_category in ('box_set', 'compilation')
      and source.range_start is not null
      and source.range_end is not null
),
format_number_matches as (
    select
        source.episode_id as source_episode_id,
        target.episode_id as target_episode_id,
        'same_recording'::text as proposed_relationship,
        case
            when source.comparison_title = target.comparison_title then 100
            when source.description is not null
                 and source.description = target.description then 95
            when source.cast_fingerprint is not null
                 and source.cast_fingerprint = target.cast_fingerprint then 95
            when source.duration_minutes is not null
                 and target.duration_minutes is not null
                 and abs(source.duration_minutes - target.duration_minutes) <= 5 then 90
            else 80
        end::integer as confidence_score,
        '["same_episode_number","format_marker"]'::jsonb
            || case when source.comparison_title = target.comparison_title
                then '["exact_normalized_title"]'::jsonb else '[]'::jsonb end
            || case when source.description is not null
                         and source.description = target.description
                then '["exact_description"]'::jsonb else '[]'::jsonb end
            || case when source.cast_fingerprint is not null
                         and source.cast_fingerprint = target.cast_fingerprint
                then '["same_cast_fingerprint"]'::jsonb else '[]'::jsonb end
            || case when source.duration_minutes is not null
                         and target.duration_minutes is not null
                         and abs(source.duration_minutes - target.duration_minutes) <= 5
                then '["duration_within_five_minutes"]'::jsonb else '[]'::jsonb end
            as match_reasons
    from classifications source
    join reference_episodes target using (episode_number)
    where source.variant_category = 'format_reissue'
),
story_title_matches as (
    select
        source.episode_id as source_episode_id,
        target.episode_id as target_episode_id,
        'same_story_different_production'::text as proposed_relationship,
        case
            when source.description is not null
                 and source.description = target.description then 95
            when source.cast_fingerprint is not null
                 and source.cast_fingerprint = target.cast_fingerprint then 95
            else 90
        end::integer as confidence_score,
        '["exact_normalized_title","different_production_marker"]'::jsonb
            || case when source.description is not null
                         and source.description = target.description
                then '["exact_description"]'::jsonb else '[]'::jsonb end
            || case when source.cast_fingerprint is not null
                         and source.cast_fingerprint = target.cast_fingerprint
                then '["same_cast_fingerprint"]'::jsonb else '[]'::jsonb end
            as match_reasons
    from classifications source
    join reference_episodes target
      on source.comparison_title = target.comparison_title
     and source.episode_id <> target.episode_id
    where source.variant_category in (
        'live_production', 'film_adaptation', 'other_production', 'special'
    )
      and source.comparison_title <> ''
),
split_compilation_titles as (
    select
        source.episode_id as source_episode_id,
        regexp_replace(
            regexp_replace(
                lower(parts.title_part),
                '(^\s*(doppelfolge|sammelfolge|steelbook\s*[0-9]+)\s*:\s*|die drei\s*\?\?\?)',
                ' ',
                'g'
            ),
            '(^\s*und\s+|[^a-z0-9äöüß]+)',
            '',
            'g'
        ) as component_title
    from classifications source
    cross join lateral regexp_split_to_table(source.episode_title, '\s*/\s*')
        as parts(title_part)
    where source.variant_category = 'compilation'
),
compilation_title_matches as (
    select
        parts.source_episode_id,
        target.episode_id as target_episode_id,
        'contains'::text as proposed_relationship,
        90::integer as confidence_score,
        '["exact_normalized_component_title"]'::jsonb as match_reasons
    from split_compilation_titles parts
    join reference_episodes target on parts.component_title = target.comparison_title
    where parts.component_title <> ''
),
all_matches as (
    select * from range_matches
    union all
    select * from format_number_matches
    union all
    select * from story_title_matches
    union all
    select * from compilation_title_matches
),
deduplicated_matches as (
    select distinct on (source_episode_id, target_episode_id, proposed_relationship)
        source_episode_id,
        target_episode_id,
        proposed_relationship,
        confidence_score,
        match_reasons
    from all_matches
    order by
        source_episode_id,
        target_episode_id,
        proposed_relationship,
        confidence_score desc,
        match_reasons::text
),
resolved as (
    select
        md5(concat_ws(':', source.source_key, target.source_key,
            matches.proposed_relationship)) as candidate_id,
        source.episode_id as source_episode_id,
        source.source_key as source_key,
        source.episode_title as source_title,
        source.variant_category,
        target.episode_id as target_episode_id,
        target.source_key as target_source_key,
        target.episode_title as target_title,
        target.episode_number as target_episode_number,
        matches.proposed_relationship,
        matches.confidence_score,
        case
            when matches.confidence_score >= 90 then 'high'
            when matches.confidence_score >= 70 then 'medium'
            else 'low'
        end as confidence_class,
        matches.match_reasons,
        source.edition_markers,
        source.range_start,
        source.range_end
    from deduplicated_matches matches
    join classifications source on source.episode_id = matches.source_episode_id
    join reference_episodes target on target.episode_id = matches.target_episode_id
),
unresolved as (
    select
        md5(concat_ws(':', source.source_key, 'none', 'unresolved')) as candidate_id,
        source.episode_id as source_episode_id,
        source.source_key as source_key,
        source.episode_title as source_title,
        source.variant_category,
        null::bigint as target_episode_id,
        null::text as target_source_key,
        null::text as target_title,
        null::bigint as target_episode_number,
        'unresolved'::text as proposed_relationship,
        0::integer as confidence_score,
        'low'::text as confidence_class,
        '["no_deterministic_target"]'::jsonb as match_reasons,
        source.edition_markers,
        source.range_start,
        source.range_end
    from classifications source
    where source.variant_category <> 'regular_episode'
      and not exists (
          select 1
          from resolved
          where resolved.source_episode_id = source.episode_id
      )
)

select * from resolved
union all
select * from unresolved
