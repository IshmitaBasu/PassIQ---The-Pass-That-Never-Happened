select match_id, event_id, candidate_index, count(*) as duplicate_count
from {{ ref('fct_candidate_pass') }}
group by 1, 2, 3
having count(*) > 1
