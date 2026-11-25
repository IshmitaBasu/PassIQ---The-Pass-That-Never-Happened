select p.*, e.home_team, e.away_team, e.home_score_pre_event, e.away_score_pre_event,
    e.team_score_pre_event, e.opponent_score_pre_event, e.game_state
from {{ ref('stg_passes') }} p
inner join {{ ref('int_event_context') }} e using (match_id, event_id, event_index)
