from __future__ import annotations

import argparse
import json
from pathlib import Path

from passiq.ingest.normalize import normalize_profile
from passiq.ingest.source import fetch_profile
from passiq.models.training import train_and_score
from passiq.quality.qa import build_qa_summary
from passiq.scoring.rankings import rank_decisions
from passiq.visuals.decisions import render_audit, render_decision, scene_for_event
from passiq.visuals.phase2 import render_phase2_visuals
from passiq.visuals.pitches import render_fixture_gallery, render_preview


def main() -> None:
    parser = argparse.ArgumentParser(prog="passiq")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("fetch", "normalize"):
        command = commands.add_parser(name)
        command.add_argument("--profile", choices=("feasibility", "tournament"), default="feasibility")
    commands.add_parser("qa")
    preview = commands.add_parser("preview-pitch")
    preview.add_argument("--output", type=Path, default=Path("reports/phase1_preview.png"))
    gallery = commands.add_parser("fixture-gallery")
    gallery.add_argument("--output-dir", type=Path, default=Path("reports/phase0_gallery"))
    gallery.add_argument("--limit", type=int, default=20)
    phase2_visuals = commands.add_parser("phase2-visuals")
    phase2_visuals.add_argument("--output-dir", type=Path, default=Path("reports/phase2"))
    commands.add_parser("train-models")
    commands.add_parser("rank-decisions")
    decision = commands.add_parser("render-decision")
    decision.add_argument("--event-id", required=True)
    decision.add_argument("--output", type=Path, required=True)
    audit = commands.add_parser("render-audit")
    audit.add_argument("--limit", type=int, default=20)
    audit.add_argument("--output-dir", type=Path, default=Path("reports/phase4"))
    args = parser.parse_args()
    if args.command == "fetch":
        result = fetch_profile(args.profile)
        print(json.dumps(result, indent=2))
    elif args.command == "normalize":
        print(json.dumps(normalize_profile(args.profile), indent=2))
    elif args.command == "qa":
        print(json.dumps(build_qa_summary(), indent=2, sort_keys=True))
    elif args.command == "preview-pitch":
        print(json.dumps(render_preview(args.output), indent=2))
    elif args.command == "phase2-visuals":
        print(json.dumps(render_phase2_visuals(args.output_dir), indent=2))
    elif args.command == "train-models":
        print(json.dumps(train_and_score(), indent=2))
    elif args.command == "rank-decisions":
        print(json.dumps(rank_decisions(), indent=2))
    elif args.command == "render-decision":
        print(json.dumps(render_decision(scene_for_event(args.event_id), args.output), indent=2))
    elif args.command == "render-audit":
        print(json.dumps(render_audit(args.limit, args.output_dir), indent=2))
    else:
        print(json.dumps(render_fixture_gallery(args.output_dir, args.limit), indent=2))


if __name__ == "__main__":
    main()

