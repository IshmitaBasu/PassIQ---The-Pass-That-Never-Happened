# Phase 4: ranked model-estimated alternatives

Phase 4 turns scored candidate destinations into reviewable decision rankings. It does not assert that a player could or would have completed any alternative pass.

## Ranking methods

`utility_high_threat` is `p_success × max(ΔxT, 0)`. It favors candidate passes that combine completion probability with positive threat.

`utility_safety_adjusted` rewards successful positive threat, then applies an explicit penalty to negative threat. The parameters live in `configs/decision.yml`; they are not hidden inside the model.

For each event, PassIQ labels the non-dominated candidates on a probability/ΔxT Pareto frontier. A candidate is dominated when another candidate has at least as much completion probability and threat, with a strict improvement in at least one dimension.

## Uncertainty and audit

The primary recommendation is rerun with a 0.05 probability penalty, conservative 0.80 ΔxT multiplier, and an open-corridor restriction. Events whose leading candidate changes are labelled `inconclusive_under_sensitivity`; the remaining events are labelled `stable_under_prespecified_sensitivity`.

The recorded pass is only compared to the candidates where `selected_pass_association_confident` is true. This guard prevents proximity-based matching from being presented as a known player choice.

Run the workflow after Phase 3:

```powershell
uv run passiq rank-decisions
uv run passiq render-audit --limit 20 --output-dir reports/phase4
```

Each rendered scene has a JSON sidecar containing match/event identity, source commit, model version, actor coordinates, visible area, candidate values, and decision status. The figures are data-based tactical illustrations, not match footage.
