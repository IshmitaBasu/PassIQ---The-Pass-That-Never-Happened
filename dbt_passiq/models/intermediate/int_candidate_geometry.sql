with candidate_base as (
    select p.match_id, p.event_id, p.event_index, p.team, p.player_id, p.player_name, p.period_id, p.period,
        p.minute, p.second, p.timestamp, p.origin_x, p.origin_y, p.end_x as actual_end_x, p.end_y as actual_end_y,
        p.is_complete, p.game_state, f.visible_area, f.actor_count, f.visible_teammate_count,
        a.frame_actor_index, a.x as candidate_x, a.y as candidate_y,
        row_number() over (partition by p.match_id, p.event_id order by a.frame_actor_index) - 1 as candidate_index,
        sqrt(power(a.x - p.origin_x, 2) + power(a.y - p.origin_y, 2)) as pass_distance,
        atan2(a.y - p.origin_y, a.x - p.origin_x) as pass_angle,
        a.x - p.origin_x as progression_x,
        sqrt(power(a.x - p.end_x, 2) + power(a.y - p.end_y, 2)) as actual_end_distance
    from {{ ref('int_pass_context') }} p
    inner join {{ ref('stg_360_frames') }} f using (match_id, event_id)
    inner join {{ ref('stg_360_actors') }} a using (match_id, event_id)
    where a.teammate and not a.actor
), defender_projections as (
    select c.match_id, c.event_id, c.candidate_index,
        sqrt(power(d.x - c.candidate_x, 2) + power(d.y - c.candidate_y, 2)) as defender_distance,
        sqrt(power(d.x - (c.origin_x + greatest(0.0, least(1.0, ((d.x - c.origin_x) * (c.candidate_x - c.origin_x) + (d.y - c.origin_y) * (c.candidate_y - c.origin_y)) / nullif(power(c.candidate_x - c.origin_x, 2) + power(c.candidate_y - c.origin_y, 2), 0))) * (c.candidate_x - c.origin_x)), 2) + power(d.y - (c.origin_y + greatest(0.0, least(1.0, ((d.x - c.origin_x) * (c.candidate_x - c.origin_x) + (d.y - c.origin_y) * (c.candidate_y - c.origin_y)) / nullif(power(c.candidate_x - c.origin_x, 2) + power(c.candidate_y - c.origin_y, 2), 0))) * (c.candidate_y - c.origin_y)), 2)) as corridor_distance
    from candidate_base c
    left join {{ ref('stg_360_actors') }} d on c.match_id = d.match_id and c.event_id = d.event_id and not d.teammate
), defensive_features as (
    select match_id, event_id, candidate_index, min(defender_distance) as closest_visible_defender_distance,
        count_if(corridor_distance <= 2.5) as defenders_in_2_5m_corridor
    from defender_projections group by 1, 2, 3
)
select c.*, d.closest_visible_defender_distance, d.defenders_in_2_5m_corridor
from candidate_base c inner join defensive_features d using (match_id, event_id, candidate_index)
