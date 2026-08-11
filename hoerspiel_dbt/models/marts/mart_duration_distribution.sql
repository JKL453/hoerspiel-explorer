select
    case
        when duration_minutes < 15 then '<15'
        when duration_minutes < 30 then '15–29'
        when duration_minutes < 45 then '30–44'
        when duration_minutes < 60 then '45–59'
        when duration_minutes < 90 then '60–89'
        else '90+'
    end as duration_bucket,
    case
        when duration_minutes < 15 then 1
        when duration_minutes < 30 then 2
        when duration_minutes < 45 then 3
        when duration_minutes < 60 then 4
        when duration_minutes < 90 then 5
        else 6
    end as bucket_order,
    count(*)::bigint as episode_count
from {{ ref('mart_episode_facts') }}
where duration_minutes is not null
group by duration_bucket, bucket_order
