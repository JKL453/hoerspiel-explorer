with pilot as (
    select
        facts.*,
        lower(facts.episode_title) as lower_title,
        coalesce(cast_counts.cast_count, 0) as cast_count,
        cast_counts.cast_fingerprint
    from {{ ref('mart_episode_facts') }} facts
    left join (
        select
            episode_id,
            count(distinct speaker_id)::integer as cast_count,
            md5(string_agg(
                concat(speaker_id, ':', role_id),
                ',' order by speaker_id, role_id
            )) as cast_fingerprint
        from {{ ref('mart_speaker_credits') }}
        group by episode_id
    ) cast_counts using (episode_id)
    where facts.series_name = 'Die Drei ???'
),
extracted as (
    select
        *,
        regexp_match(
            lower_title,
            'folgen?\s*0*([0-9]+)\s*(?:-|–|bis|und)\s*0*([0-9]+)'
        ) as episode_range_match,
        lower_title ~ '(fanbox|einsteigerbox)' as is_fanbox,
        lower_title ~ '(steelbook|sammelbox)' as is_container,
        lower_title ~ '(doppelfolge|sammelfolge)' as is_compilation,
        lower_title ~ '(lp[ -]?edition|vinyl|neuauflage|reissue)' as is_format_reissue,
        lower_title ~ '(^|[^a-zäöüß])(live|live-dvd|live &|live and)([^a-zäöüß]|$)'
            or lower_title ~ 'usb-stick' as is_live,
        lower_title ~ '(hörspiel zum film|original-hörspiel zum kinofilm|kinofilm)'
            as is_film,
        lower_title ~ '(adventskalender|special|top secret edition)' as is_special,
        lower_title ~ '(lesung|liest:?|radio show|soundtrack|originalmusik|alexa-skill|welt der hörspiele)'
            as is_other_production,
        lower_title ~ '/' as has_title_separator
    from pilot
),
normalized as (
    select
        *,
        case
            when is_fanbox or is_container then 'box_set'
            when is_compilation or has_title_separator then 'compilation'
            when is_format_reissue then 'format_reissue'
            when is_live then 'live_production'
            when is_film then 'film_adaptation'
            when is_special then 'special'
            when is_other_production then 'other_production'
            when episode_number between 1 and 999 then 'regular_candidate'
            else 'unknown'
        end as base_category,
        nullif((episode_range_match)[1], '')::integer as range_start,
        nullif((episode_range_match)[2], '')::integer as range_end,
        concat_ws(
            ',',
            case when is_fanbox then 'fanbox' end,
            case when is_container then 'container' end,
            case when is_compilation then 'compilation' end,
            case when is_format_reissue then 'format_reissue' end,
            case when is_live then 'live' end,
            case when is_film then 'film' end,
            case when is_special then 'special' end,
            case when is_other_production then 'other_production' end,
            case when has_title_separator then 'multi_title' end
        ) as edition_markers,
        regexp_replace(
            regexp_replace(
                regexp_replace(
                    regexp_replace(
                        lower_title,
                        '(die drei\s*\?\?\?|special\s+[0-9]{4}\s*[-:]?)',
                        ' ',
                        'g'
                    ),
                    '\([^)]*(lp[ -]?edition|vinyl|hörspiel zum film|kinofilm|live|dvd|special)[^)]*\)',
                    ' ',
                    'g'
                ),
                '\s*[-–]\s*(live|lp[ -]?edition|special).*$',
                ' ',
                'g'
            ),
            '^\s*(und\s+)?',
            '',
            'g'
        ) as comparison_title
    from extracted
)

select
    episode_id,
    source_key,
    episode_number,
    episode_title,
    description,
    duration_minutes,
    release_date,
    order_number,
    cast_count,
    cast_fingerprint,
    base_category,
    range_start,
    range_end,
    edition_markers,
    regexp_replace(comparison_title, '[^a-z0-9äöüß]+', '', 'g') as comparison_title,
    has_title_separator
from normalized
