from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

import duckdb
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from sklearn.calibration import calibration_curve
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from passiq.paths import project_root

FEATURES = ["origin_x", "origin_y", "destination_x", "destination_y", "pass_distance", "pass_angle", "progression_x", "closest_visible_defender_distance", "defenders_in_2_5m_corridor", "visible_teammate_count", "actor_count"]


def _split_matches(match_ids: list[int], seed: int) -> dict[str, list[int]]:
    ids = np.array(sorted(match_ids)); rng = np.random.default_rng(seed); rng.shuffle(ids)
    train_end, validation_end = int(len(ids) * .70), int(len(ids) * .85)
    return {"train": ids[:train_end].tolist(), "validation": ids[train_end:validation_end].tolist(), "test": ids[validation_end:].tolist()}


def _ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1); result = 0.0
    for lo, hi in itertools.pairwise(edges):
        mask = (p >= lo) & ((p < hi) if hi < 1 else (p <= hi))
        if mask.any(): result += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return float(result)


def _metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    return {"brier": float(brier_score_loss(y, p)), "log_loss": float(log_loss(y, p, labels=[0, 1])), "roc_auc": float(roc_auc_score(y, p)), "calibration_error": _ece(y, p)}


def _direction_map(passes: pd.DataFrame) -> dict[str, bool]:
    direction = passes.assign(dx=passes.end_x - passes.origin_x).groupby(["match_id", "team", "period_id"]).dx.mean()
    return {"|".join(map(str, key)): bool(value >= 0) for key, value in direction.items()}


def _normal_x(x: pd.Series, frame: pd.DataFrame, directions: dict[str, bool]) -> np.ndarray:
    keys = frame.match_id.astype(str) + "|" + frame.team + "|" + frame.period_id.astype(str)
    right = keys.map(directions).astype("boolean").fillna(True).to_numpy(bool)
    return np.where(right, x.to_numpy(float), 120 - x.to_numpy(float))


def _xt_grid(train_passes: pd.DataFrame, train_events: pd.DataFrame, directions: dict[str, bool], nx: int = 12, ny: int = 8) -> np.ndarray:
    moves = train_passes[train_passes.is_complete & ~train_passes.set_piece].copy()
    shots = train_events[train_events.type.eq("Shot")].copy()
    for frame, start, end in ((moves, "origin_x", "end_x"),):
        frame["sx"] = _normal_x(frame[start], frame, directions); frame["ex"] = _normal_x(frame[end], frame, directions)
        frame["sy"], frame["ey"] = frame.origin_y, frame.end_y
    shots["sx"] = _normal_x(shots.location_x, shots, directions); shots["sy"] = shots.location_y
    def zone(x: pd.Series, y: pd.Series) -> np.ndarray:
        return np.minimum(nx - 1, (x.to_numpy() / 120 * nx).astype(int)) + nx * np.minimum(ny - 1, (y.to_numpy() / 80 * ny).astype(int))
    move_start, move_end, shot_zone = zone(moves.sx, moves.sy), zone(moves.ex, moves.ey), zone(shots.sx, shots.sy)
    cells = nx * ny; move_count = np.bincount(move_start, minlength=cells); shot_count = np.bincount(shot_zone, minlength=cells)
    goal = shots.shot_outcome.eq("Goal").to_numpy(int); goals = np.bincount(shot_zone, weights=goal, minlength=cells)
    transition = np.zeros((cells, cells)); np.add.at(transition, (move_start, move_end), 1)
    transition = transition / np.maximum(move_count[:, None], 1)
    total = move_count + shot_count; p_shot = (shot_count + 1) / (total + 2); p_move = 1 - p_shot
    global_goal = (goals.sum() + 1) / (shot_count.sum() + 2); p_goal = (goals + global_goal) / (shot_count + 1)
    return np.linalg.solve(np.eye(cells) - p_move[:, None] * transition, p_shot * p_goal).reshape(ny, nx)


def _lookup_xt(grid: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    ny, nx = grid.shape; ix = np.clip((x / 120 * nx).astype(int), 0, nx - 1); iy = np.clip((y / 80 * ny).astype(int), 0, ny - 1)
    return grid[iy, ix]


def train_and_score(root: Path | None = None) -> dict:
    root = root or project_root(); config = yaml.safe_load((root / "configs" / "model.yml").read_text())
    con = duckdb.connect(str(root / "data" / "gold" / "passiq.duckdb"), read_only=True)
    passes = con.execute("select * from fct_pass").df(); events = con.execute("select * from stg_events").df(); candidates = con.execute("select * from fct_candidate_pass").df(); con.close()
    selected = candidates[candidates.selected_pass_association_confident].drop_duplicates(["match_id", "event_id"])
    observed = passes.merge(selected[["match_id", "event_id", "closest_visible_defender_distance", "defenders_in_2_5m_corridor", "visible_teammate_count", "actor_count"]], on=["match_id", "event_id"], how="left")
    observed = observed[(~observed.set_piece) & observed.origin_x.notna() & observed.end_x.notna()].copy()
    observed["destination_x"], observed["destination_y"] = observed.end_x, observed.end_y
    observed["pass_distance"] = np.hypot(observed.destination_x-observed.origin_x, observed.destination_y-observed.origin_y)
    observed["pass_angle"] = np.arctan2(observed.destination_y-observed.origin_y, observed.destination_x-observed.origin_x)
    observed["progression_x"] = observed.destination_x-observed.origin_x
    splits = _split_matches(observed.match_id.unique().tolist(), config["seed"])
    (root / "manifests" / "splits.json").write_text(json.dumps(splits, indent=2) + "\n")
    train, validation, test = (observed[observed.match_id.isin(splits[name])] for name in ("train", "validation", "test"))
    model = Pipeline([("imputer", SimpleImputer(strategy="median", add_indicator=True)), ("scale", StandardScaler()), ("logistic", LogisticRegression(max_iter=1000, C=1.0, random_state=config["seed"]))])
    model.fit(train[FEATURES], train.is_complete.astype(int)); val_raw = model.predict_proba(validation[FEATURES])[:, 1]
    calibrator = IsotonicRegression(out_of_bounds="clip").fit(val_raw, validation.is_complete.astype(int))
    test_raw = model.predict_proba(test[FEATURES])[:, 1]; test_p = calibrator.transform(test_raw); y_test = test.is_complete.astype(int).to_numpy()
    directions = _direction_map(passes); grid = _xt_grid(passes[passes.match_id.isin(splits["train"])], events[events.match_id.isin(splits["train"])], directions, *config["xt"]["grid"])
    score = candidates.rename(columns={"candidate_x": "destination_x", "candidate_y": "destination_y"}).copy()
    score["pass_distance"] = np.hypot(score.destination_x-score.origin_x, score.destination_y-score.origin_y); score["pass_angle"] = np.arctan2(score.destination_y-score.origin_y, score.destination_x-score.origin_x); score["progression_x"] = score.destination_x-score.origin_x
    score["p_success"] = calibrator.transform(model.predict_proba(score[FEATURES])[:, 1])
    sx, ex = _normal_x(score.origin_x, score, directions), _normal_x(score.destination_x, score, directions)
    score["xt_start"], score["xt_end"] = _lookup_xt(grid, sx, score.origin_y.to_numpy()), _lookup_xt(grid, ex, score.destination_y.to_numpy())
    score["xt_delta"] = score.xt_end - score.xt_start; score["expected_positive_threat"] = score.p_success * np.maximum(score.xt_delta, 0)
    score["coverage_flag"] = "visible_360_candidate"; score["model_version"] = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:12]
    root.joinpath("data/gold").mkdir(parents=True, exist_ok=True); score.to_parquet(root / "data/gold/candidate_scores.parquet", index=False)
    rng = np.random.default_rng(config["seed"]); briers=[]; test_ids=np.array(splits["test"])
    for _ in range(config["uncertainty"]["bootstrap_match_resamples"]):
        sampled=rng.choice(test_ids, len(test_ids), replace=True); mask=test.match_id.isin(sampled); briers.append(brier_score_loss(test.loc[mask, "is_complete"], test_p[mask]))
    metrics = {"test": _metrics(y_test, test_p), "test_brier_95pct_match_bootstrap": [float(np.quantile(briers,.025)), float(np.quantile(briers,.975))], "rows": {k: len(v) for k,v in {"train":train,"validation":validation,"test":test,"candidate_scores":score}.items()}, "model_version": score.model_version.iloc[0]}
    report = root / "reports" / "evaluation"; report.mkdir(parents=True, exist_ok=True); (report / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    models_dir = root / "models"; models_dir.mkdir(exist_ok=True)
    joblib.dump({"model":model,"calibrator":calibrator,"features":FEATURES,"model_version":score.model_version.iloc[0]}, models_dir / "xpass_logistic.joblib")
    np.savez(root / "models" / "xt_grid.npz", grid=grid, nx=config["xt"]["grid"][0], ny=config["xt"]["grid"][1])
    (root / "manifests" / "model_release.json").write_text(json.dumps(metrics, indent=2) + "\n")
    coefficients = model.named_steps["logistic"].coef_[0][:len(FEATURES)]
    (report / "feature_importance.json").write_text(json.dumps(dict(zip(FEATURES, map(float, coefficients), strict=True)), indent=2) + "\n")
    frac, mean = calibration_curve(y_test, test_p, n_bins=10, strategy="quantile")
    figure, axis = plt.subplots(figsize=(8, 6)); axis.plot([0, 1], [0, 1], "--", color="#777777", label="Perfect calibration"); axis.plot(mean, frac, marker="o", color="#43AA8B", label="Calibrated xPass")
    axis.set(xlabel="Predicted completion probability", ylabel="Observed completion rate", title="PassIQ xPass calibration — held-out matches", xlim=(0, 1), ylim=(0, 1)); axis.legend()
    axis.text(.03, .94, f"Brier: {metrics['test']['brier']:.3f}\n95% match-bootstrap CI: {metrics['test_brier_95pct_match_bootstrap'][0]:.3f}–{metrics['test_brier_95pct_match_bootstrap'][1]:.3f}", transform=axis.transAxes, va="top")
    for extension in ("png", "svg"): figure.savefig(report / f"xpass_calibration.{extension}", dpi=160, bbox_inches="tight")
    plt.close(figure)
    return {"metrics":metrics,"calibration": {"observed":frac.tolist(),"predicted":mean.tolist()}, "grid":grid.tolist()}
