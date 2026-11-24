select c.match_id, c.event_id
from {{ ref('fct_candidate_pass') }} c
left join {{ ref('fct_pass') }} p using (match_id, event_id)
where p.event_id is null
