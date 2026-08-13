with catalog as (
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
),
extracted as (
    select
        *,
        regexp_match(
            lower_title,
            'folgen?\s*0*([0-9]+)\s*(?:-|–|bis|und)\s*0*([0-9]+)'
        ) as episode_range_match,
        lower_title ~ '(fanbox|einsteigerbox)' as is_fanbox,
        lower_title ~ '(steelbook|sammelbox|hörspielbox|hörspiel-box|jubiläumsbox|komplettbox|sammleredition|in einer box|collector.?s box)'
            as is_container,
        lower_title ~ '(doppelfolge|sammelfolge|gesamtausgabe)' as is_compilation,
        lower_title ~ '(lp[ -]?edition|vinyl|neuauflage|reissue|remastered)' as is_format_reissue,
        lower_title ~ '(^|[^a-zäöüß])(live|live-dvd|live &|live and)([^a-zäöüß]|$)'
            or lower_title ~ 'usb-stick' as is_live,
        lower_title ~ '(hörspiel zum film|original-hörspiel zum kinofilm|kinofilm|filmfassung)'
            as is_film,
        lower_title ~ '(adventskalender|special|top secret edition|sonderfolge)'
            as is_special,
        lower_title ~ '(hörbuch|audiobook|lesung|liest:?)' as is_audiobook,
        lower_title ~ '(radio show|soundtrack|originalmusik|alexa-skill|welt der hörspiele)'
            as is_other_production,
        series_name = 'Die Drei ???'
            and label_name = 'Tudor'
            and episode_number between 1 and 8 as is_dialect,
        lower_title ~ '/'
            and lower_title !~ '(teil\s*)?[0-9]+\s*/\s*[0-9]+'
            as has_title_separator,
        case
            when series_name = 'John Sinclair'
             and lower(coalesce(label_name, '')) ~ '(tonstudio braun|^tsb)'
                then 'tonstudio_braun'
            when series_name = 'John Sinclair' then 'edition_2000'
            else 'main'
        end as production_line_key,
        case
            when series_name = 'John Sinclair'
             and lower(coalesce(label_name, '')) ~ '(tonstudio braun|^tsb)'
                then 'Tonstudio Braun'
            when series_name = 'John Sinclair' then 'Edition 2000'
            else 'Hauptserie'
        end as production_line_label,
        case
            when series_name = 'John Sinclair'
             and lower(coalesce(label_name, '')) ~ '(tonstudio braun|^tsb)' then 20
            else 10
        end as production_line_order
    from catalog
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
            when is_dialect or is_special then 'special'
            when is_audiobook or is_other_production then 'other_production'
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
            case when is_special or is_dialect then 'special' end,
            case when is_audiobook then 'audiobook' end,
            case when is_dialect then 'dialect' end,
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
                '\s*[-–]\s*(live|lp[ -]?edition|special).*$'
                , ' ', 'g'
            ),
            '^\s*(und\s+)?',
            '',
            'g'
        ) as comparison_title
    from extracted
)

select
    series_id,
    series_name,
    franchise_name,
    production_line_key,
    production_line_label,
    production_line_order,
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
