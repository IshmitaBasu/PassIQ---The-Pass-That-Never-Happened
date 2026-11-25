from __future__ import annotations

import json
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import pandas as pd
from mplsoccer import Pitch

from passiq.paths import project_root
from passiq.visuals.scene import SceneProvenance, SceneSpec


def scene_for_event(event_id: str, root: Path | None = None) -> SceneSpec:
    root = root or project_root()
    ranked = pd.read_parquet(root / "data" / "gold" / "decision_rankings.parquet")
    rows = ranked[ranked.event_id.eq(event_id)].sort_values("rank_high_threat")
    if rows.empty:
        raise ValueError(f"No ranked candidates for {event_id}")
    row = rows.iloc[0]
    con = duckdb.connect(str(root / "data" / "gold" / "passiq.duckdb"), read_only=True)
    actors = con.execute("select frame_actor_index, x, y, teammate, actor, keeper from fct_360_actor where match_id=? and event_id=?", [int(row.match_id), event_id]).df().to_dict("records")
    visible_area = con.execute("select visible_area from fct_360_frame where match_id=? and event_id=?", [int(row.match_id), event_id]).fetchone()[0]
    con.close()
    manifest = json.loads((root / "manifests" / "source_data.json").read_text())
    candidate_columns = ["candidate_index", "destination_x", "destination_y", "p_success", "xt_delta", "expected_positive_threat", "model_estimated_frontier", "rank_high_threat", "rank_safety_adjusted", "is_nearest_actual_end", "selected_pass_association_confident"]
    return SceneSpec(SceneProvenance(int(row.match_id), event_id, row.model_version, manifest["source"]["commit"]), (float(row.origin_x), float(row.origin_y)), (float(row.actual_end_x), float(row.actual_end_y)), json.loads(visible_area), actors, rows[candidate_columns].to_dict("records"), str(row.decision_status))


def render_decision(scene: SceneSpec, output: Path) -> dict:
    pitch = Pitch(pitch_type="statsbomb", pitch_color="#173F35", line_color="#EAF2EF")
    figure, axis = pitch.draw(figsize=(16, 9))
    vertices = list(zip(scene.visible_area[::2], scene.visible_area[1::2], strict=True))
    pitch.polygon([vertices], ax=axis, color="#6FCF97", alpha=0.13)
    actors = pd.DataFrame(scene.actors)
    opponents, teammates, actor = actors[~actors.teammate], actors[actors.teammate & ~actors.actor], actors[actors.actor]
    pitch.scatter(opponents.x, opponents.y, ax=axis, s=65, color="#E76F51", edgecolors="white", label="Visible opponent")
    pitch.scatter(teammates.x, teammates.y, ax=axis, s=65, color="#43AA8B", edgecolors="white", label="Visible teammate")
    pitch.scatter(actor.x, actor.y, ax=axis, s=110, color="#5DADE2", edgecolors="white", label="Pass actor")
    pitch.arrows(*scene.origin, *scene.actual_end, ax=axis, color="white", width=2.5, headwidth=5, headlength=5, label="Recorded pass")
    for candidate in scene.candidates[:6]:
        color = "#F5B700" if candidate["model_estimated_frontier"] else "#A0A0A0"
        pitch.arrows(*scene.origin, candidate["destination_x"], candidate["destination_y"], ax=axis, color=color, alpha=0.8, width=1.1, headwidth=3, headlength=3, linestyle="--")
        right_side = candidate["destination_x"] > 90
        axis.annotate(
            f"#{candidate['rank_high_threat']} p={candidate['p_success']:.2f} dxT={candidate['xt_delta']:.3f}",
            (candidate["destination_x"], candidate["destination_y"]),
            xytext=(-5 if right_side else 5, 3),
            textcoords="offset points",
            ha="right" if right_side else "left",
            color="white",
            fontsize=7,
        )
    axis.set_title(f"Model-estimated pass options | match {scene.provenance.match_id} | {scene.decision_status.replace('_', ' ')}", fontsize=14, pad=14)
    axis.legend(loc="upper right", frameon=True)
    figure.text(0.5, 0.02, "Solid: observed recorded pass | dashed: model-estimated option | data-based tactical illustration, not match footage", ha="center", color="white", fontsize=9)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(figure)
    sidecar = output.with_suffix(output.suffix + ".json")
    sidecar.write_text(json.dumps(scene.as_dict(), indent=2) + "\n")
    return scene.as_dict()


def render_audit(limit: int = 20, output_dir: Path | None = None, root: Path | None = None) -> dict:
    root = root or project_root()
    output_dir = output_dir or root / "reports" / "phase4"
    ranked = pd.read_parquet(root / "data" / "gold" / "decision_rankings.parquet")
    events = ranked[ranked.selected_pass_association_confident].sort_values(["recommendation_stable", "expected_positive_threat"], ascending=[False, False]).drop_duplicates("event_id").head(limit)
    results = []
    for item in events.itertuples():
        scene = scene_for_event(item.event_id, root)
        results.append(render_decision(scene, output_dir / f"{item.event_id}.png"))
        render_decision(scene, output_dir / f"{item.event_id}.svg")
    (output_dir / "audit_manifest.json").write_text(json.dumps(results, indent=2) + "\n")
    return {"rendered": len(results), "output_dir": str(output_dir)}
