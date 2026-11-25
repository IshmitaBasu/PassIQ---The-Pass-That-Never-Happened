# PassIQ — The Pass That Never Happened

PassIQ reconstructs the visible passing options around historical StatsBomb 360 events, scores them with transparent models, and presents the chosen action alongside *model-estimated* alternatives. It does not claim that an alternative pass would have succeeded or changed the match.

## Phase 0–3 status

This repository contains the scoped 2022 FIFA World Cup pipeline for source retrieval, immutable raw-file manifests, normalization to Parquet, dbt/DuckDB candidate marts, and first-release xPass/xT scoring. The selected initial proof-of-concept event comes from the Argentina–France final (`3869685`). Source files are fetched only from the commit pinned in `manifests/source_data.json`.

## Quick start

```powershell
uv sync --extra dev
uv run passiq fetch --profile feasibility
uv run passiq normalize --profile feasibility
uv run passiq qa
uv run passiq preview-pitch --output reports/phase1_preview.png
uv run dbt build --project-dir dbt_passiq --profiles-dir dbt_passiq
uv run passiq phase2-visuals --output-dir reports/phase2
uv run pytest
```

`--profile feasibility` downloads three auditable fixtures. `--profile tournament` downloads the full 2022 World Cup scope. Both runs are idempotent: a raw file is retained only when its checksum agrees with the manifest record.

## Data and media policy

StatsBomb Open Data is the source. The code does not redistribute raw match data. See [data policy](docs/data_policy.md), [research questions](docs/research_questions.md), and [visual style guide](docs/visual_style_guide.md). Public outputs must include data attribution, source revision, match/event identity, and the notice: “data-based tactical illustration, not match footage.”

## Commands

| Command | Purpose |
| --- | --- |
| `passiq fetch --profile feasibility` | retrieve and checksum raw source files |
| `passiq normalize --profile feasibility` | write normalized Silver Parquet tables |
| `passiq qa` | write and print reconciliation counts |
| `passiq preview-pitch` | render a source-grounded freeze-frame PNG |
| `dbt build --project-dir dbt_passiq --profiles-dir dbt_passiq` | materialize and test Gold marts |
| `passiq phase2-visuals` | render network, candidate-geometry, and pre-model zone figures |

The `Makefile` preserves the planned command contract for environments with GNU Make.

