from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from passiq.ingest.source import load_manifest, match_ids_for_profile, raw_path
from passiq.paths import project_root


def _location(value: object) -> tuple[float | None, float | None]:
    if isinstance(value, list) and len(value) >= 2:
        return float(value[0]), float(value[1])
    return None, None


def _value(payload: dict, *keys: str) -> object:
    current: object = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _name(payload: object) -> str | None:
    return payload.get("name") if isinstance(payload, dict) else None


def _period(value: object) -> tuple[int | None, str | None]:
    """Normalize StatsBomb's numeric period while accepting a named variant."""
    if isinstance(value, dict):
        period_id = value.get("id")
        return (int(period_id) if period_id is not None else None, value.get("name"))
    if value is None:
        return None, None
    period_id = int(value)
    labels = {1: "First Half", 2: "Second Half", 3: "First Extra Time", 4: "Second Extra Time", 5: "Penalty Shootout"}
    return period_id, labels.get(period_id, f"Period {period_id}")


SCHEMAS = {
    "matches": pa.schema([
        ("match_id", pa.int64()), ("match_date", pa.string()), ("kick_off", pa.string()),
        ("competition_stage", pa.string()), ("home_team_id", pa.int64()), ("home_team", pa.string()),
        ("away_team_id", pa.int64()), ("away_team", pa.string()), ("home_score", pa.int64()),
        ("away_score", pa.int64()),
    ]),
    "events": pa.schema([
        ("match_id", pa.int64()), ("event_id", pa.string()), ("event_index", pa.int64()),
        ("period_id", pa.int64()), ("period", pa.string()), ("minute", pa.int64()), ("second", pa.int64()),
        ("timestamp", pa.string()), ("type", pa.string()), ("team", pa.string()),
        ("player_id", pa.int64()), ("player_name", pa.string()), ("possession", pa.int64()),
        ("location_x", pa.float64()), ("location_y", pa.float64()), ("shot_outcome", pa.string()),
    ]),
    "passes": pa.schema([
        ("match_id", pa.int64()), ("event_id", pa.string()), ("event_index", pa.int64()),
        ("team", pa.string()), ("player_id", pa.int64()), ("player_name", pa.string()),
        ("period_id", pa.int64()), ("period", pa.string()), ("minute", pa.int64()), ("second", pa.int64()),
        ("timestamp", pa.string()), ("origin_x", pa.float64()), ("origin_y", pa.float64()),
        ("end_x", pa.float64()), ("end_y", pa.float64()), ("recipient_id", pa.int64()),
        ("recipient_name", pa.string()), ("outcome", pa.string()), ("is_complete", pa.bool_()),
        ("pass_type", pa.string()), ("set_piece", pa.bool_()),
    ]),
    "frames": pa.schema([
        ("match_id", pa.int64()), ("event_id", pa.string()), ("visible_area", pa.string()),
        ("actor_count", pa.int64()), ("visible_teammate_count", pa.int64()),
    ]),
    "actors": pa.schema([
        ("match_id", pa.int64()), ("event_id", pa.string()), ("frame_actor_index", pa.int64()),
        ("x", pa.float64()), ("y", pa.float64()), ("teammate", pa.bool_()),
        ("actor", pa.bool_()), ("keeper", pa.bool_()),
    ]),
}


def normalize_profile(profile: str, root: Path | None = None) -> dict[str, int]:
    root = root or project_root()
    manifest = load_manifest(root)
    match_ids = match_ids_for_profile(profile, manifest, root)
    matches_path = raw_path("matches/43/106.json", root)
    if not matches_path.exists():
        raise FileNotFoundError(f"Match metadata missing; run `passiq fetch --profile {profile}` first.")
    match_metadata = json.loads(matches_path.read_text(encoding="utf-8"))
    match_rows = [{
        "match_id": int(match["match_id"]), "match_date": match.get("match_date"), "kick_off": match.get("kick_off"),
        "competition_stage": _name(match.get("competition_stage")),
        "home_team_id": _value(match, "home_team", "home_team_id"), "home_team": _value(match, "home_team", "home_team_name"),
        "away_team_id": _value(match, "away_team", "away_team_id"), "away_team": _value(match, "away_team", "away_team_name"),
        "home_score": match.get("home_score"), "away_score": match.get("away_score"),
    } for match in match_metadata if int(match["match_id"]) in match_ids]
    if len(match_rows) != len(match_ids):
        raise ValueError("The pinned match index does not contain every requested match ID.")
    silver = root / "data" / "silver"
    silver.mkdir(parents=True, exist_ok=True)
    writers: dict[str, pq.ParquetWriter] = {}
    row_counts = {name: 0 for name in SCHEMAS}
    for name in SCHEMAS:
        (silver / f"{name}.parquet").unlink(missing_ok=True)

    try:
        match_table = pa.Table.from_pylist(match_rows, schema=SCHEMAS["matches"])
        writers["matches"] = pq.ParquetWriter(silver / "matches.parquet", SCHEMAS["matches"], compression="snappy")
        writers["matches"].write_table(match_table)
        row_counts["matches"] = len(match_rows)
        for match_id in match_ids:
            event_path = raw_path(f"events/{match_id}.json", root)
            frame_path = raw_path(f"three-sixty/{match_id}.json", root)
            if not event_path.exists() or not frame_path.exists():
                raise FileNotFoundError(f"Raw files missing for {match_id}; run `passiq fetch --profile {profile}` first.")
            events = json.loads(event_path.read_text(encoding="utf-8"))
            frames = json.loads(frame_path.read_text(encoding="utf-8"))
            event_rows: list[dict] = []
            pass_rows: list[dict] = []
            frame_rows: list[dict] = []
            actor_rows: list[dict] = []
            for event in events:
                x, y = _location(event.get("location"))
                event_id = event["id"]
                period_id, period_name = _period(event.get("period"))
                event_rows.append({
                "match_id": match_id, "event_id": event_id, "event_index": event.get("index"),
                "period_id": period_id, "period": period_name, "minute": event.get("minute"), "second": event.get("second"),
                "timestamp": event.get("timestamp"), "type": _name(event.get("type")),
                "team": _name(event.get("team")), "player_id": _value(event, "player", "id"),
                "player_name": _name(event.get("player")), "possession": event.get("possession"),
                "location_x": x, "location_y": y, "shot_outcome": _name(_value(event, "shot", "outcome")),
                })
                if _name(event.get("type")) == "Pass":
                    pass_data = event.get("pass", {})
                    end_x, end_y = _location(pass_data.get("end_location"))
                    pass_rows.append({
                    "match_id": match_id, "event_id": event_id, "event_index": event.get("index"),
                    "team": _name(event.get("team")), "player_id": _value(event, "player", "id"),
                    "player_name": _name(event.get("player")), "period_id": period_id, "period": period_name,
                    "minute": event.get("minute"), "second": event.get("second"), "timestamp": event.get("timestamp"),
                    "origin_x": x, "origin_y": y, "end_x": end_x, "end_y": end_y,
                    "recipient_id": _value(pass_data, "recipient", "id"),
                    "recipient_name": _name(pass_data.get("recipient")),
                    "outcome": _name(pass_data.get("outcome")),
                    "is_complete": _name(pass_data.get("outcome")) is None,
                    "pass_type": _name(pass_data.get("type")),
                    "set_piece": _name(pass_data.get("type")) in {"Corner", "Free Kick", "Throw-in", "Goal Kick", "Kick Off"},
                    })
            for frame in frames:
                event_id = frame["event_uuid"]
                actors = frame.get("freeze_frame", [])
                frame_rows.append({
                "match_id": match_id, "event_id": event_id,
                "visible_area": json.dumps(frame.get("visible_area", [])),
                "actor_count": len(actors),
                "visible_teammate_count": sum(bool(a.get("teammate")) and not bool(a.get("actor")) for a in actors),
                })
                for actor_index, actor in enumerate(actors):
                    x, y = _location(actor.get("location"))
                    actor_rows.append({
                    "match_id": match_id, "event_id": event_id, "frame_actor_index": actor_index,
                    "x": x, "y": y, "teammate": bool(actor.get("teammate")),
                    "actor": bool(actor.get("actor")), "keeper": bool(actor.get("keeper")),
                    })
            tables = {"events": event_rows, "passes": pass_rows, "frames": frame_rows, "actors": actor_rows}
            for name, rows in tables.items():
                table = pa.Table.from_pylist(rows, schema=SCHEMAS[name])
                if name not in writers:
                    writers[name] = pq.ParquetWriter(silver / f"{name}.parquet", SCHEMAS[name], compression="snappy")
                writers[name].write_table(table)
                row_counts[name] += len(rows)
    finally:
        for writer in writers.values():
            writer.close()
    return row_counts

