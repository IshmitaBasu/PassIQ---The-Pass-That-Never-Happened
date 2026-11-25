with event_match as (
    select e.*, m.home_team, m.away_team,
        case
            when e.type = 'Shot' and e.shot_outcome = 'Goal' then e.team
            when e.type = 'Own Goal Against' and e.team = m.home_team then m.away_team
            when e.type = 'Own Goal Against' and e.team = m.away_team then m.home_team
        end as scoring_team
    from {{ ref('stg_events') }} e
    inner join {{ ref('stg_matches') }} m using (match_id)
), scored as (
    select *,
        coalesce(sum(case when scoring_team = home_team then 1 else 0 end) over (partition by match_id order by event_index rows between unbounded preceding and 1 preceding), 0) as home_score_pre_event,
        coalesce(sum(case when scoring_team = away_team then 1 else 0 end) over (partition by match_id order by event_index rows between unbounded preceding and 1 preceding), 0) as away_score_pre_event
    from event_match
)
select *,
    case when team = home_team then home_score_pre_event else away_score_pre_event end as team_score_pre_event,
    case when team = home_team then away_score_pre_event else home_score_pre_event end as opponent_score_pre_event,
    case
        when (case when team = home_team then home_score_pre_event else away_score_pre_event end) > (case when team = home_team then away_score_pre_event else home_score_pre_event end) then 'leading'
        when (case when team = home_team then home_score_pre_event else away_score_pre_event end) < (case when team = home_team then away_score_pre_event else home_score_pre_event end) then 'trailing'
        else 'drawing'
    end as game_state
from scored
