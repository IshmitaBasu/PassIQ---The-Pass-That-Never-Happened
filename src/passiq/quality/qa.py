from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from passiq.paths import project_root


def _load(name: str, root: Path) -> pd.DataFrame:
    return pd.read_parquet(root / "data" / "silver" / f"{name}.parquet")


def build_qa_summary(root: Path | None = None) -> dict:
    root = root or project_root()
    matches, events, passes, frames, actors = (_load(name, root) for name in ("matches", "events", "passes", "frames", "actors"))
    joined = passes.merge(frames[["match_id", "event_id", "visible_teammate_count"]], on=["match_id", "event_id"], how="inner")
    event_coordinate_columns = [(events, "location_x", "location_y"), (passes, "origin_x", "origin_y"), (passes, "end_x", "end_y")]
    invalid_event_coordinates = 0
    for table, x_col, y_col in event_coordinate_columns:
        valid = table[x_col].notna() & table[y_col].notna()
        invalid_event_coordinates += int(((table.loc[valid, x_col] < 0) | (table.loc[valid, x_col] > 120) | (table.loc[valid, y_col] < 0) | (table.loc[valid, y_col] > 80)).sum())
    valid_actor_coordinates = actors["x"].notna() & actors["y"].notna()
    extended_actor_coordinates = int(((actors.loc[valid_actor_coordinates, "x"] < 0) | (actors.loc[valid_actor_coordinates, "x"] > 120) | (actors.loc[valid_actor_coordinates, "y"] < 0) | (actors.loc[valid_actor_coordinates, "y"] > 80)).sum())
    duplicate_actor_keys = int(actors.duplicated(["match_id", "event_id", "frame_actor_index"]).sum())
    summary = {
        "matches": len(matches), "matches_without_events": int((~matches["match_id"].isin(events["match_id"])).sum()),
        "events": len(events), "passes": len(passes),
        "frames": len(frames), "actors": len(actors), "joined_pass_frames": len(joined),
        "joined_pass_rate": round(float(len(joined) / len(passes)), 6) if len(passes) else 0.0,
        "candidate_visible_teammates": int(frames["visible_teammate_count"].sum()),
        "frames_without_candidates": int((frames["visible_teammate_count"] == 0).sum()),
        "missing_event_frame_links": int((~frames["event_id"].isin(events["event_id"])).sum()),
        "invalid_event_coordinates": invalid_event_coordinates,
        "freeze_frame_actor_coordinates_outside_pitch": extended_actor_coordinates,
        "duplicate_actor_keys": duplicate_actor_keys,
        "passes_missing_locations": int(passes[["origin_x", "origin_y", "end_x", "end_y"]].isna().any(axis=1).sum()),
    }
    destination = root / "data" / "silver" / "qa_summary.json"
    destination.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary

