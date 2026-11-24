# Data policy and attribution

## Source and pin

The Phase 0–1 source is StatsBomb Open Data at the exact Git commit stored in `manifests/source_data.json`. Every fetched file receives a SHA-256 checksum, source URL, UTC fetch time, and match ID in that manifest. A changed upstream branch never silently changes a run.

At this pinned revision, the upstream README asks publishers of research, analysis, or insights based on the data to name **StatsBomb** as the data source and use its logo from the StatsBomb Media Pack. The PassIQ public-asset checklist therefore requires both. The repository did not expose a standalone `LICENSE` file at the pinned revision; this policy records the published Terms & Conditions text rather than inventing a licence.

## Storage and redistribution

Raw JSON and generated Parquet are ignored by Git. Before publishing code, derived datasets, model artifacts, or media, re-check the upstream repository licence and attribution requirements at the pinned revision. Do not commit or redistribute raw match files through this project by default.

## Identity and visual integrity

StatsBomb 360 freeze-frame actors are positional points. They are never assigned a player identity from proximity. Recorded event recipients may be named only where source event data supplies them. Public graphics credit StatsBomb Open Data and distinguish observed data from model estimates and illustrative animation.

## Limits

A 360 frame is an observed instant with camera coverage, not continuous tracking. The project will not interpolate movement between freeze frames or portray an estimated pass as match footage.

