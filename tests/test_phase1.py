from __future__ import annotations

import json
from pathlib import Path

from passiq.ingest.normalize import normalize_profile
from passiq.ingest.source import sha256_file
from passiq.quality.qa import build_qa_summary


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_normalization_and_qa_preserve_anonymous_actor_keys(tmp_path: Path) -> None:
    manifest = {
        "profiles": {"feasibility": [99]},
        "source": {"commit": "test", "raw_base_url": "https://example.test"},
        "files": {},
    }
    _write_json(tmp_path / "manifests/source_data.json", manifest)
    _write_json(tmp_path / "data/raw/matches/43/106.json", [{
        "match_id": 99, "match_date": "2022-01-01", "kick_off": "12:00:00.000",
        "competition_stage": {"name": "Group Stage"},
        "home_team": {"home_team_id": 1, "home_team_name": "A"},
        "away_team": {"away_team_id": 2, "away_team_name": "B"}, "home_score": 1, "away_score": 0,
    }])
    _write_json(tmp_path / "data/raw/events/99.json", [{
        "id": "pass-1", "index": 1, "period": {"name": "First Half"}, "minute": 1, "second": 2,
        "timestamp": "00:01:02.000", "type": {"name": "Pass"}, "team": {"name": "A"},
        "player": {"id": 7, "name": "Known Player"}, "location": [10, 20], "possession": 1,
        "pass": {"end_location": [30, 40], "recipient": {"id": 8, "name": "Known Recipient"}},
    }])
    _write_json(tmp_path / "data/raw/three-sixty/99.json", [{
        "event_uuid": "pass-1", "visible_area": [0, 0, 120, 0, 120, 80],
        "freeze_frame": [
            {"location": [10, 20], "teammate": True, "actor": True, "keeper": False},
            {"location": [30, 40], "teammate": True, "actor": False, "keeper": False},
            {"location": [40, 50], "teammate": False, "actor": False, "keeper": False},
        ],
    }])
    row_counts = normalize_profile("feasibility", tmp_path)
    assert row_counts["matches"] == 1
    assert row_counts["passes"] == 1
    assert row_counts["actors"] == 3
    import pandas as pd

    actors = pd.read_parquet(tmp_path / "data/silver/actors.parquet")
    assert "player_id" not in actors.columns
    summary = build_qa_summary(tmp_path)
    assert summary["joined_pass_frames"] == 1
    assert summary["matches_without_events"] == 0
    assert summary["candidate_visible_teammates"] == 1
    assert summary["invalid_event_coordinates"] == 0


def test_sha256_file_is_stable(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_text("passiq", encoding="utf-8")
    assert sha256_file(path) == "87cdaa70c7fc5be31b62aa37744716b0136376f14f3cfa316b3002cd83ddfbc9"


def test_numeric_period_has_a_stable_label() -> None:
    from passiq.ingest.normalize import _period

    assert _period(2) == (2, "Second Half")


def test_visual_fixture_metadata_covers_required_phase_one_cases() -> None:
    cases = json.loads((Path(__file__).parent / "fixtures" / "visual_cases.json").read_text(encoding="utf-8"))["cases"]
    assert {"typical", "touchline", "edge_of_pitch", "ambiguous_receiver_geometry", "sparse_frame", "period_direction_switch"} <= cases.keys()

