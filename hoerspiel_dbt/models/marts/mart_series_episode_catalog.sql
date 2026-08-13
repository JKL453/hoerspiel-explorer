with facts as (
    select * from {{ ref('mart_episode_facts') }}
),
classifications as (
    select * from {{ ref('episode_variant_classifications') }}
),
enriched as (
    select
        facts.*,
        classifications.variant_category,
        classifications.production_line_key,
        classifications.production_line_label,
        classifications.production_line_order,
        classifications.machine_category,
        classifications.classification_source,
        classifications.edition_markers,
        case
            when concat(',', classifications.edition_markers, ',') like '%,dialect,%'
                then 'dialect'
            when concat(',', classifications.edition_markers, ',') like '%,audiobook,%'
                then 'audiobook'
            when classifications.variant_category = 'regular_episode' then 'regular'
            when classifications.variant_category = 'format_reissue' then 'reissue'
            when classifications.variant_category in ('box_set', 'compilation') then 'collection'
            when classifications.variant_category = 'live_production' then 'live'
            when classifications.variant_category = 'film_adaptation' then 'film'
            when classifications.variant_category = 'special' then 'special'
            when classifications.variant_category = 'other_production' then 'other'
            else 'unknown'
        end as category_key
    from facts
    join classifications using (episode_id)
)

select
    *,
    case category_key
        when 'regular' then 'Reguläre Folgen'
        when 'special' then 'Specials'
        when 'dialect' then 'Dialektfolgen'
        when 'audiobook' then 'Hörbücher & Lesungen'
        when 'live' then 'Live-Produktionen'
        when 'film' then 'Filmhörspiele'
        when 'reissue' then 'Neuauflagen & Formate'
        when 'collection' then 'Boxen & Sammlungen'
        when 'other' then 'Andere Produktionen'
        else 'Unklar'
    end as category_label,
    case category_key
        when 'regular' then 10
        when 'special' then 20
        when 'dialect' then 30
        when 'audiobook' then 40
        when 'live' then 50
        when 'film' then 60
        when 'reissue' then 70
        when 'collection' then 80
        when 'other' then 90
        else 100
    end as category_order
from enriched
