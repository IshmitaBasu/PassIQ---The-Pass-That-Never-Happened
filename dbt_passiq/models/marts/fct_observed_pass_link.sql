select match_id, event_id, event_index, team, player_id, player_name, recipient_id, recipient_name,
    origin_x, origin_y, end_x, end_y, is_complete, period_id, period, minute, second, game_state
from {{ ref('fct_pass') }} where recipient_id is not null
