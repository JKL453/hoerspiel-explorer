with overrides as (
    select
        source_key,
        max(nullif(reviewed_category, '')) as reviewed_category,
        max(nullif(reviewed_markers, '')) as reviewed_markers
    from {{ ref('episode_variant_reviews') }}
    where review_decision = 'accept'
      and (nullif(reviewed_category, '') is not null
        or nullif(reviewed_markers, '') is not null)
    group by source_key
)

select overrides.source_key
from overrides
left join {{ ref('episode_variant_classifications') }} classifications using (source_key)
where classifications.source_key is null
   or classifications.classification_source <> 'reviewed'
   or (overrides.reviewed_category is not null
       and classifications.variant_category <> overrides.reviewed_category)
   or (overrides.reviewed_markers is not null
       and classifications.edition_markers <> overrides.reviewed_markers)
