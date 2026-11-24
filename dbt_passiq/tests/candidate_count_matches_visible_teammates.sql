with candidate_counts as (
    select match_id, event_id, count(*) as candidate_count
    from {{ ref('fct_candidate_pass') }}
    group by 1, 2
)
select f.match_id, f.event_id, f.visible_teammate_count, coalesce(c.candidate_count, 0) as candidate_count
from {{ ref('fct_360_frame') }} f
inner join {{ ref('fct_pass') }} p using (match_id, event_id)
left join candidate_counts c using (match_id, event_id)
where f.visible_teammate_count <> coalesce(c.candidate_count, 0)
