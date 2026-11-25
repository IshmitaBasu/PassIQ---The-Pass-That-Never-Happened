.PHONY: setup data transform dbt train score qa preview phase2-visuals test

setup:
	uv sync --extra dev

data:
	uv run passiq fetch --profile tournament

transform:
	uv run passiq normalize --profile tournament

dbt:
	uv run dbt build --project-dir dbt_passiq --profiles-dir dbt_passiq

train:
	uv run passiq train-models

score: train

qa:
	uv run passiq qa

preview:
	uv run passiq preview-pitch --output reports/phase1_preview.png

phase2-visuals:
	uv run passiq phase2-visuals --output-dir reports/phase2

test:
	uv run pytest

