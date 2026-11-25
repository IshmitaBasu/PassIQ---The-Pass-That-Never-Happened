with ranked as (
    select *, row_number() over (partition by match_id, event_id order by actual_end_distance, candidate_index) as actual_end_rank,
        lead(actual_end_distance) over (partition by match_id, event_id order by actual_end_distance, candidate_index) as next_actual_end_distance
    from {{ ref('int_candidate_geometry') }}
)
select *, actual_end_rank = 1 as is_nearest_actual_end,
    case when actual_end_rank = 1 and actual_end_distance <= 2.0 and (next_actual_end_distance is null or next_actual_end_distance - actual_end_distance >= 0.5) then true else false end as selected_pass_association_confident
from ranked
