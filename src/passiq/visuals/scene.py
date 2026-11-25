from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SceneProvenance:
    match_id: int
    event_id: str
    model_version: str
    source_commit: str
    template: str = "decision"


@dataclass(frozen=True)
class SceneSpec:
    provenance: SceneProvenance
    origin: tuple[float, float]
    actual_end: tuple[float, float]
    visible_area: list[float]
    actors: list[dict]
    candidates: list[dict]
    decision_status: str
    ranking_method: str = "high_threat"

    def as_dict(self) -> dict:
        return asdict(self)
