# Phase 2 analytics engineering

The dbt/DuckDB graph turns the Phase 1 Parquet layer into documented analytics marts. It preserves anonymous 360 positions, adds pre-event score context from ordered goal events, and generates one candidate row for every visible teammate other than the actor.

## Marts

- `fct_pass`: recorded pass context, including pre-event score and leading/drawing/trailing state.
- `fct_360_frame` and `fct_360_actor`: observed 360 geometry; actor rows remain anonymous.
- `fct_candidate_pass`: candidate endpoint, distance, angle, progression, closest visible defender, passing-corridor pressure, coverage fields, and an explicit selected-pass association confidence flag.
- `fct_observed_pass_link`: named passing-network links grounded only in recorded event recipients.

Selected-pass association is deliberately conservative: the nearest visible teammate must fall within 2.0 coordinate units of the recorded pass end and be at least 0.5 units clearer than the next closest visible teammate. Ambiguous and unmatched rows remain in the data but do not become selected-candidate claims.

## Full-scope build result

The verified World Cup build created 375,508 candidate rows across 57,330 pass events with at least one visible teammate. Only 7,085 rows meet the conservative selected-pass association rule. The observed-recipient mart contains 63,735 recorded links. This separation is intentional: named network edges are factual event data, while candidate endpoints stay anonymous.

Run the graph with `uv run dbt build --project-dir dbt_passiq --profiles-dir dbt_passiq`, then render the Phase 2 outputs with `uv run passiq phase2-visuals --output-dir reports/phase2`. The zone graphic is explicitly a pass-end density preview, **not xT**; Phase 3 trains xT using training matches only.
