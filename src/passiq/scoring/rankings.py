from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from passiq.paths import project_root


def _frontier(frame: pd.DataFrame) -> pd.Series:
    probability, threat = frame.p_success.to_numpy(), frame.xt_delta.to_numpy()
    result = []
    for index in range(len(frame)):
        dominates = (
            (probability >= probability[index])
            & (threat >= threat[index])
            & ((probability > probability[index]) | (threat > threat[index]))
        ).any()
        result.append(not dominates)
    return pd.Series(result, index=frame.index)


def _frontier_all(scores: pd.DataFrame) -> pd.Series:
    """Compute each event's two-dimensional Pareto frontier in one sorted pass."""
    event_codes = pd.MultiIndex.from_arrays([scores.match_id, scores.event_id]).factorize()[0]
    probability = scores.p_success.to_numpy()
    threat = scores.xt_delta.to_numpy()
    order = np.lexsort((-threat, -probability, event_codes))
    frontier = np.zeros(len(scores), dtype=bool)
    current_event = -1
    best_threat = -np.inf
    for index in order:
        if event_codes[index] != current_event:
            current_event = event_codes[index]
            best_threat = -np.inf
        if threat[index] >= best_threat:
            frontier[index] = True
            best_threat = threat[index]
    return pd.Series(frontier, index=scores.index)


def _utilities(frame: pd.DataFrame, config: dict, probability: pd.Series | None = None, delta: pd.Series | None = None) -> pd.DataFrame:
    output = frame.copy()
    probability = probability if probability is not None else output.p_success
    delta = delta if delta is not None else output.xt_delta
    output["utility_high_threat"] = probability * delta.clip(lower=0)
    setting = config["utilities"]["safety_adjusted"]
    output["utility_safety_adjusted"] = probability * (1 + setting["positive_xt_multiplier"] * delta.clip(lower=0)) - setting["negative_xt_penalty"] * (-delta.clip(upper=0))
    return output


def rank_decisions(root: Path | None = None) -> dict:
    root = root or project_root()
    config = yaml.safe_load((root / "configs" / "decision.yml").read_text())
    scores = pd.read_parquet(root / "data" / "gold" / "candidate_scores.parquet")
    scores = _utilities(scores, config)
    scores["model_estimated_frontier"] = _frontier_all(scores)
    for utility in ("utility_high_threat", "utility_safety_adjusted"):
        scores[f"rank_{utility.removeprefix('utility_')}"] = scores.groupby(["match_id", "event_id"])[utility].rank(method="first", ascending=False).astype(int)
    scores["chosen_pass_reliably_matched"] = scores.selected_pass_association_confident
    scores["chosen_pass_frontier"] = scores.selected_pass_association_confident & scores.model_estimated_frontier
    group_keys = [scores.match_id, scores.event_id]
    variants: dict[str, pd.Series] = {"base": scores.groupby(["match_id", "event_id"])["utility_high_threat"].idxmax()}
    penalty = config["sensitivity"]["probability_penalty"]
    variants["probability_penalty"] = _utilities(scores, config, (scores.p_success - penalty).clip(lower=0))["utility_high_threat"].groupby(group_keys).idxmax()
    multiplier = config["sensitivity"]["xt_conservative_multiplier"]
    variants["conservative_xt"] = _utilities(scores, config, delta=scores.xt_delta * multiplier)["utility_high_threat"].groupby(group_keys).idxmax()
    allowed = scores[scores.defenders_in_2_5m_corridor <= config["sensitivity"]["corridor_candidate_exclusion_threshold"]]
    variants["open_corridor_only"] = allowed.groupby(["match_id", "event_id"])["utility_high_threat"].idxmax()
    sensitivity = pd.DataFrame(variants)
    sensitivity["recommendation_stable"] = sensitivity.nunique(axis=1).eq(1)
    sensitivity = sensitivity.reset_index()
    scores = scores.merge(sensitivity[["match_id", "event_id", "recommendation_stable"]], on=["match_id", "event_id"], how="left")
    scores["decision_status"] = np.where(scores.recommendation_stable, "stable_under_prespecified_sensitivity", "inconclusive_under_sensitivity")
    output = root / "data" / "gold"
    scores.to_parquet(output / "decision_rankings.parquet", index=False)
    sensitivity.to_parquet(output / "decision_sensitivity.parquet", index=False)
    summary = {"candidate_rows": len(scores), "events": int(scores[["match_id", "event_id"]].drop_duplicates().shape[0]), "stable_events": int(sensitivity.recommendation_stable.sum()), "reliably_matched_chosen_passes": int(scores.selected_pass_association_confident.sum())}
    report = root / "reports" / "evaluation"
    report.mkdir(parents=True, exist_ok=True)
    (report / "decision_ranking_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary
