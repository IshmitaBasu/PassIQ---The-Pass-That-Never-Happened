# Research questions and success criteria

## Questions

1. For a historical pass with a StatsBomb 360 snapshot, which visible *anonymous* teammate locations form feasible geometric passing options?
2. How do calibrated estimates of completion probability and positional threat compare for the selected pass and available options?
3. How do the distributions of those estimates vary by recorded player, team, game state, and role once the relevant denominators and coverage are visible?

The observed action is factual. Completion estimates, xT values, frontiers, and unattempted alternatives are predictions, not missed opportunities or causal claims.

## Phase 0 success criteria

- A source commit, match IDs, data policy, scope, split policy, and visual vocabulary are documented.
- Three World Cup matches are profiled for event/frame linkage and missingness.
- A real selected pass can be joined to its 360 frame and rendered with source identity.

## Baselines and validation policy

- xPass begins with logistic regression over observed attempted passes; later 360-enhanced models remain separate.
- xT is fitted only on training matches and records its grid/direction configuration.
- Splits are by match. Training, calibration/validation, and final test matches never overlap.
- No future event, final score, later frame, or inferred actor identity appears in a pre-decision feature.

## MVP boundary

The MVP is normalization, visible-option geometry, xPass/xT baselines, transparent ranking, a decision-pitch PNG/SVG, and one freeze-frame-based tactical clip. Transition-risk modeling, live ingestion, FastAPI, and continuous player tracking are outside this phase.

