from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import imageio_ffmpeg
import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import animation
from mplsoccer import Pitch

from passiq.paths import project_root
from passiq.visuals.decisions import scene_for_event
from passiq.visuals.scene import SceneSpec

FPS = 12
DURATION_SECONDS = 12


def clip_phase(frame: int, fps: int = FPS) -> str:
    second = frame / fps
    if second < 2:
        return "source"
    if second < 5:
        return "recorded_pass"
    if second < 9:
        return "alternatives"
    if second < 11:
        return "comparison"
    return "limitations"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _draw_static_scene(axis: plt.Axes, scene: SceneSpec) -> Pitch:
    pitch = Pitch(pitch_type="statsbomb", pitch_color="#173F35", line_color="#EAF2EF")
    pitch.draw(ax=axis)
    vertices = list(zip(scene.visible_area[::2], scene.visible_area[1::2], strict=True))
    pitch.polygon([vertices], ax=axis, color="#6FCF97", alpha=0.13)
    actors = pd.DataFrame(scene.actors)
    opponents = actors[~actors.teammate]
    teammates = actors[actors.teammate & ~actors.actor]
    actor = actors[actors.actor]
    pitch.scatter(opponents.x, opponents.y, ax=axis, s=65, color="#E76F51", edgecolors="white")
    pitch.scatter(teammates.x, teammates.y, ax=axis, s=65, color="#43AA8B", edgecolors="white")
    pitch.scatter(actor.x, actor.y, ax=axis, s=110, color="#5DADE2", edgecolors="white")
    return pitch


def _make_animation(scene: SceneSpec, fps: int, duration: int) -> animation.FuncAnimation:
    figure, axis = plt.subplots(figsize=(12.8, 7.2), facecolor="#173F35")
    pitch = _draw_static_scene(axis, scene)
    title = axis.text(60, -5, "", ha="center", color="white", fontsize=16, weight="bold")
    caption = axis.text(60, 86, "", ha="center", color="white", fontsize=10)
    annotations: list[object] = []

    def update(frame: int) -> list[object]:
        nonlocal annotations
        for artist in annotations:
            artist.remove()
        annotations = []
        phase = clip_phase(frame, fps)
        if phase == "source":
            title.set_text("The Pass That Never Happened")
            caption.set_text(
                f"Match {scene.provenance.match_id} | event {scene.provenance.event_id[:8]} | observed 360 freeze frame"
            )
        elif phase == "recorded_pass":
            title.set_text("Recorded pass")
            caption.set_text("Observed event: solid arrow. Player locations are one freeze frame.")
            annotations.append(pitch.arrows(*scene.origin, *scene.actual_end, ax=axis, color="white", width=2.8, headwidth=5, headlength=5))
        elif phase in {"alternatives", "comparison"}:
            title.set_text("Model-estimated alternatives")
            caption.set_text("Dashed arrows are estimates, not observed outcomes.")
            annotations.append(pitch.arrows(*scene.origin, *scene.actual_end, ax=axis, color="white", width=2.2, headwidth=4, headlength=4))
            reveal = min(len(scene.candidates), 1 + int((frame / fps - 5) * 1.5))
            for candidate in scene.candidates[: max(reveal, 0)]:
                color = "#F5B700" if candidate["model_estimated_frontier"] else "#A0A0A0"
                annotations.append(pitch.arrows(*scene.origin, candidate["destination_x"], candidate["destination_y"], ax=axis, color=color, alpha=0.85, width=1.2, headwidth=3, headlength=3, linestyle="--"))
                if phase == "comparison":
                    annotations.append(axis.annotate(f"p={candidate['p_success']:.0%}  dxT={candidate['xt_delta']:.3f}", (candidate["destination_x"], candidate["destination_y"]), color="white", fontsize=8))
        else:
            title.set_text("Model estimate — not match footage")
            caption.set_text("Actors do not move: this is a data-based tactical illustration. Source: StatsBomb Open Data.")
        return [title, caption, *annotations]

    return animation.FuncAnimation(figure, update, frames=fps * duration, interval=1000 / fps, blit=False)


def render_decision_clip(
    event_id: str,
    output_dir: Path | None = None,
    root: Path | None = None,
    ranking_method: str = "high_threat",
    fps: int = FPS,
    duration: int = DURATION_SECONDS,
) -> dict:
    if not 10 <= duration <= 20:
        raise ValueError("Decision clips must be 10–20 seconds long")
    root = root or project_root()
    output_dir = output_dir or root / "reports" / "media"
    output_dir.mkdir(parents=True, exist_ok=True)
    scene = scene_for_event(event_id, root, ranking_method)
    base = output_dir / f"decision_{event_id}_{ranking_method}"
    mp4_path, gif_path = base.with_suffix(".mp4"), base.with_suffix(".gif")
    mpl.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()
    clip = _make_animation(scene, fps, duration)
    clip.save(
        mp4_path,
        writer=animation.FFMpegWriter(
            fps=fps, codec="libx264", bitrate=2500, extra_args=["-pix_fmt", "yuv420p"]
        ),
    )
    clip.save(gif_path, writer=animation.PillowWriter(fps=fps))
    plt.close("all")
    manifest = {
        "template": "decision",
        "renderer_version": "phase6-v1",
        "renderer_sha256": _sha256(Path(__file__)),
        "event_id": event_id,
        "match_id": scene.provenance.match_id,
        "model_version": scene.provenance.model_version,
        "source_commit": scene.provenance.source_commit,
        "ranking_method": ranking_method,
        "fps": fps,
        "duration_seconds": duration,
        "resolution": [1280, 720],
        "utc_rendered_at": datetime.now(UTC).isoformat(),
        "notice": "data-based tactical illustration, not match footage",
        "outputs": {
            "mp4": {"path": str(mp4_path), "codec": "h264", "sha256": _sha256(mp4_path)},
            "gif": {"path": str(gif_path), "sha256": _sha256(gif_path)},
        },
        "scene": scene.as_dict(),
    }
    sidecar = base.with_suffix(".render_manifest.json")
    sidecar.write_text(json.dumps(manifest, indent=2) + "\n")
    return {"mp4": str(mp4_path), "gif": str(gif_path), "manifest": str(sidecar)}
