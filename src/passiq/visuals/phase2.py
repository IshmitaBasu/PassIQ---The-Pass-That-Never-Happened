from __future__ import annotations

from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
from mplsoccer import Pitch

from passiq.paths import project_root


def _connection(root: Path) -> duckdb.DuckDBPyConnection:
    database = root / "data" / "gold" / "passiq.duckdb"
    if not database.exists():
        raise FileNotFoundError("dbt marts are missing; run the dbt build command first.")
    return duckdb.connect(str(database), read_only=True)


def _network(connection: duckdb.DuckDBPyConnection, output: Path) -> None:
    links = connection.execute("""
        select player_name, recipient_name, avg(origin_x) origin_x, avg(origin_y) origin_y,
               avg(end_x) end_x, avg(end_y) end_y, count(*) passes
        from fct_observed_pass_link where team = 'Argentina' and is_complete
        group by 1, 2 having count(*) >= 5
    """).df()
    pitch = Pitch(pitch_type="statsbomb", pitch_color="#173F35", line_color="#EAF2EF")
    figure, axis = pitch.draw(figsize=(16, 9))
    nodes: dict[str, list[tuple[float, float]]] = {}
    for row in links.itertuples(index=False):
        pitch.arrows(row.origin_x, row.origin_y, row.end_x, row.end_y, ax=axis, color="white", alpha=0.45, width=min(5, 0.5 + row.passes / 5), headwidth=4, headlength=4)
        nodes.setdefault(row.player_name, []).append((row.origin_x, row.origin_y))
        nodes.setdefault(row.recipient_name, []).append((row.end_x, row.end_y))
    for name, locations in nodes.items():
        x, y = (sum(point[i] for point in locations) / len(locations) for i in (0, 1))
        pitch.scatter(x, y, ax=axis, s=170, color="#43AA8B", edgecolors="white", linewidth=1)
        axis.annotate(name.split()[-1], (x, y), color="white", ha="center", va="center", fontsize=8)
    axis.set_title("Argentina observed completed-pass network — World Cup 2022", fontsize=16, pad=16)
    figure.text(0.5, 0.025, "Recorded event recipients only · StatsBomb Open Data · no 360 identity inference", ha="center", fontsize=9)
    figure.savefig(output, dpi=150, bbox_inches="tight")
    plt.close(figure)


def _candidate_pitch(connection: duckdb.DuckDBPyConnection, output: Path) -> None:
    event = connection.execute("""
        select match_id, event_id, any_value(origin_x) origin_x, any_value(origin_y) origin_y,
               any_value(actual_end_x) actual_end_x, any_value(actual_end_y) actual_end_y
        from fct_candidate_pass where match_id = 3869685 group by 1, 2 order by count(*) desc, event_id limit 1
    """).df().iloc[0]
    candidates = connection.execute("select * from fct_candidate_pass where match_id = ? and event_id = ? order by candidate_index", [int(event.match_id), str(event.event_id)]).df()
    pitch = Pitch(pitch_type="statsbomb", pitch_color="#173F35", line_color="#EAF2EF")
    figure, axis = pitch.draw(figsize=(16, 9))
    pitch.scatter(candidates.candidate_x, candidates.candidate_y, ax=axis, s=95, color="#43AA8B", edgecolors="white", label="Visible teammate (anonymous)")
    for row in candidates.itertuples(index=False):
        pitch.arrows(event.origin_x, event.origin_y, row.candidate_x, row.candidate_y, ax=axis, color="#F5B700", alpha=0.55, width=1.2, headwidth=3, headlength=3, linestyle="--")
    pitch.scatter(event.origin_x, event.origin_y, ax=axis, s=140, color="#5DADE2", edgecolors="white", label="Pass actor")
    pitch.arrows(event.origin_x, event.origin_y, event.actual_end_x, event.actual_end_y, ax=axis, color="white", width=2.5, headwidth=5, headlength=5, label="Recorded pass")
    axis.set_title(f"Visible candidate geometry | match {event.match_id} | event {event.event_id}", fontsize=15, pad=16)
    axis.legend(loc="upper right", bbox_to_anchor=(0.98, 0.98), frameon=True, facecolor="#173F35", edgecolor="#EAF2EF", labelcolor="white")
    figure.text(0.5, 0.018, "Dashed arrows are unscored visible options, not predicted outcomes · StatsBomb Open Data", ha="center", fontsize=9)
    figure.savefig(output, dpi=150, bbox_inches="tight")
    plt.close(figure)


def _zone_preview(connection: duckdb.DuckDBPyConnection, output: Path) -> None:
    ends = connection.execute("select end_x, end_y from fct_pass where end_x is not null and end_y is not null").df()
    pitch = Pitch(pitch_type="statsbomb", pitch_color="#173F35", line_color="#EAF2EF")
    figure, axis = pitch.draw(figsize=(16, 9))
    bins = pitch.bin_statistic(ends.end_x, ends.end_y, statistic="count", bins=(12, 8))
    heatmap = pitch.heatmap(bins, ax=axis, cmap="magma", edgecolors="#EAF2EF", alpha=0.82)
    figure.colorbar(heatmap, ax=axis, shrink=0.72, label="Recorded pass ends")
    axis.set_title("Pre-model zone preview: recorded pass-end density", fontsize=16, pad=16)
    figure.text(0.5, 0.025, "Not xT — xT is trained in Phase 3 · StatsBomb Open Data", ha="center", fontsize=9)
    figure.savefig(output, dpi=150, bbox_inches="tight")
    plt.close(figure)


def render_phase2_visuals(output_dir: Path, root: Path | None = None) -> dict[str, str]:
    root = root or project_root()
    output_dir.mkdir(parents=True, exist_ok=True)
    connection = _connection(root)
    try:
        outputs = {"observed_network": output_dir / "observed_network.png", "candidate_pitch": output_dir / "candidate_pitch.png", "zone_preview": output_dir / "zone_preview.png"}
        _network(connection, outputs["observed_network"])
        _candidate_pitch(connection, outputs["candidate_pitch"])
        _zone_preview(connection, outputs["zone_preview"])
        return {name: str(path) for name, path in outputs.items()}
    finally:
        connection.close()
