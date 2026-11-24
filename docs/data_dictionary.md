# Phase 1 data dictionary

| Table | Grain | Key fields | Notes |
| --- | --- | --- | --- |
| `matches` | one recorded fixture | `match_id`, date, kickoff, stage, teams, score | Fixture metadata comes from the pinned competition-season index. |
| `events` | one recorded event | `match_id`, `event_id`, `event_index`, period ID/label, time, team, player, location | Event player identity comes from the event source. |
| `passes` | one recorded pass | period ID/label, origin/end, recorded recipient, completion, set-piece type | Recipient is a recorded event field, not a 360 identity inference. |
| `frames` | one 360 frame | `match_id`, `event_id`, visible-area polygon, actor/candidate counts | Joins to `events.event_id`. |
| `actors` | one positional frame actor | `match_id`, `event_id`, `frame_actor_index`, location, teammate/actor/keeper flags | Deliberately contains no player ID. |

Event and pass coordinates must lie in the 120 × 80 StatsBomb pitch range. Freeze-frame actor coordinates are stored raw. Some legitimately fall slightly outside that range because the captured camera/calibration geometry includes the pitch boundary. QA reports this separately as a coverage characteristic, rather than silently clipping, dropping, or calling it an invalid event location.

