from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import yaml
from mplsoccer import Pitch

from passiq.paths import project_root


def _candidate_frames(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    passes = pd.read_parquet(root / "data" / "silver" / "passes.parquet")
    frames = pd.read_parquet(root / "data" / "silver" / "frames.parquet")
    actors = pd.read_parquet(root / "data" / "silver" / "actors.parquet")
    manifest = json.loads((root / "manifests" / "source_data.json").read_text(encoding="utf-8"))
    candidates = passes.merge(frames, on=["match_id", "event_id"], how="inner").dropna(subset=["origin_x", "origin_y", "end_x", "end_y"])
    if candidates.empty:
        raise ValueError("No pass/360 frame joins available for preview.")
    return candidates, actors, manifest


def _render_scene(chosen: pd.Series, actors: pd.DataFrame, manifest: dict, output: Path) -> dict:
    frame_actors = actors[(actors.match_id == chosen.match_id) & (actors.event_id == chosen.event_id)]
    pitch = Pitch(pitch_type="statsbomb", pitch_color="#173F35", line_color="#EAF2EF", linewidth=1.2)
    fig, axis = pitch.draw(figsize=(16, 9))
    visible_area = json.loads(chosen.visible_area)
    if len(visible_area) >= 6 and len(visible_area) % 2 == 0:
        vertices = list(zip(visible_area[::2], visible_area[1::2], strict=True))
        pitch.polygon([vertices], ax=axis, color="#B7E4C7", alpha=0.12, edgecolor="#B7E4C7", linewidth=1)
    opponents = frame_actors[~frame_actors.teammate]
    teammates = frame_actors[frame_actors.teammate & ~frame_actors.actor]
    event_actor = frame_actors[frame_actors.actor]
    pitch.scatter(opponents.x, opponents.y, ax=axis, s=95, color="#E76F51", edgecolors="white", linewidth=0.7, label="Visible opponent")
    pitch.scatter(teammates.x, teammates.y, ax=axis, s=95, color="#43AA8B", edgecolors="white", linewidth=0.7, label="Visible teammate (anonymous)")
    pitch.scatter(event_actor.x, event_actor.y, ax=axis, s=130, color="#5DADE2", edgecolors="white", linewidth=1, label="Pass actor")
    pitch.arrows(chosen.origin_x, chosen.origin_y, chosen.end_x, chosen.end_y, ax=axis, color="white", width=2.5, headwidth=5, headlength=5, label="Recorded pass")
    axis.set_title(f"PassIQ Phase 1 source preview | match {chosen.match_id} | event {chosen.event_id}", color="#18211E", fontsize=14, pad=18)
    fig.text(0.5, 0.035, f"StatsBomb Open Data · source {manifest['source']['commit'][:12]} · data-based tactical illustration — not match footage", ha="center", fontsize=9)
    axis.legend(loc="upper center", bbox_to_anchor=(0.5, -0.07), ncol=4, frameon=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150, bbox_inches="tight", metadata={"Match ID": str(chosen.match_id), "Event ID": str(chosen.event_id), "Source commit": manifest["source"]["commit"]})
    plt.close(fig)
    sidecar = output.with_suffix(output.suffix + ".json")
    provenance = {"match_id": int(chosen.match_id), "event_id": chosen.event_id, "selection_rule": "joined pass with most visible teammates; then match ID and event index", "source_commit": manifest["source"]["commit"], "renderer": "passiq.visuals.pitches.render_preview", "output": str(output)}
    sidecar.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    return provenance


def render_preview(output: Path, root: Path | None = None) -> dict:
    """Render the joined pass frame with the most visible teammate candidates."""
    root = root or project_root()
    candidates, actors, manifest = _candidate_frames(root)
    scope = yaml.safe_load((root / "configs" / "scope.yml").read_text(encoding="utf-8"))
    vertical_slice_match_id = scope["initial_vertical_slice"]["match_id"]
    vertical_slice = candidates[candidates.match_id == vertical_slice_match_id]
    if vertical_slice.empty:
        raise ValueError(f"Configured vertical-slice match {vertical_slice_match_id} is not normalized.")
    chosen = vertical_slice.sort_values(["visible_teammate_count", "event_index"], ascending=[False, True]).iloc[0]
    return _render_scene(chosen, actors, manifest, output)


def render_fixture_gallery(output_dir: Path, limit: int = 20, root: Path | None = None) -> list[dict]:
    """Render a deterministic gallery of real joined pass/360 scenes for visual QA."""
    root = root or project_root()
    candidates, actors, manifest = _candidate_frames(root)
    selected = candidates.sort_values(["visible_teammate_count", "match_id", "event_index"], ascending=[False, True, True]).head(limit)
    if len(selected) < limit:
        raise ValueError(f"Only {len(selected)} joined pass frames available; requested {limit}.")
    output_dir.mkdir(parents=True, exist_ok=True)
    return [_render_scene(row, actors, manifest, output_dir / f"scene_{index:02d}.png") for index, (_, row) in enumerate(selected.iterrows(), start=1)]

