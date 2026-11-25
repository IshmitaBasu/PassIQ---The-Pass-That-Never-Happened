from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from components.data import event_catalog, event_label, load_rankings, match_label

from passiq.paths import project_root
from passiq.visuals.decisions import render_decision, scene_for_event

ROOT = project_root()
st.set_page_config(page_title="PassIQ | Decision Room", page_icon="⚽", layout="wide")


@st.cache_data(show_spinner=False)
def _rankings() -> pd.DataFrame:
    return load_rankings(ROOT)


@st.cache_data(show_spinner=False)
def _catalog(rankings: pd.DataFrame) -> pd.DataFrame:
    return event_catalog(ROOT, rankings)


def _export(event_id: str, utility: str, extension: str) -> Path:
    directory = ROOT / "reports" / "dashboard_cache"
    target = directory / f"{event_id}_{utility}.{extension}"
    if not target.exists():
        render_decision(scene_for_event(event_id, ranking_method=utility), target)
    return target


def _candidate_table(rows: pd.DataFrame, utility: str) -> pd.DataFrame:
    rank = f"rank_{utility}"
    columns = [
        "candidate_index",
        rank,
        "p_success",
        "xt_delta",
        "expected_positive_threat",
        "model_estimated_frontier",
        "defenders_in_2_5m_corridor",
        "is_nearest_actual_end",
    ]
    table = rows.sort_values(rank)[columns].rename(
        columns={
            "candidate_index": "option",
            rank: "rank",
            "p_success": "p(success)",
            "xt_delta": "ΔxT",
            "expected_positive_threat": "expected positive threat",
            "model_estimated_frontier": "Pareto frontier",
            "defenders_in_2_5m_corridor": "defenders in corridor",
            "is_nearest_actual_end": "nearest recorded end",
        }
    )
    return table.round({"p(success)": 3, "ΔxT": 3, "expected positive threat": 3})


def main() -> None:
    st.title("PassIQ Decision Room")
    st.caption("Historical StatsBomb 360 decision reconstruction — model estimates, not observed outcomes.")
    rankings = _rankings()
    catalog = _catalog(rankings)

    with st.sidebar:
        st.header("Select evidence")
        match_ids = sorted(catalog.match_id.dropna().astype(int).unique().tolist())
        selected_match = st.selectbox(
            "Match",
            match_ids,
            format_func=lambda value: match_label(catalog[catalog.match_id.eq(value)].iloc[0]),
        )
        match_events = catalog[catalog.match_id.eq(selected_match)].sort_values(["minute", "second"])
        event_ids = match_events.event_id.tolist()
        selected_event = st.selectbox(
            "Pass event",
            event_ids,
            format_func=lambda value: event_label(match_events[match_events.event_id.eq(value)].iloc[0]),
        )
        utility = st.radio(
            "Ranking view",
            options=("high_threat", "safety_adjusted"),
            format_func=lambda value: "High threat" if value == "high_threat" else "Safety adjusted",
        )

    event = match_events[match_events.event_id.eq(selected_event)].iloc[0]
    rows = rankings[(rankings.match_id.eq(selected_match)) & (rankings.event_id.eq(selected_event))]
    top = rows.sort_values(f"rank_{utility}").iloc[0]
    confidence = bool(top.selected_pass_association_confident)

    st.subheader(f"{event.home_team} {int(event.home_score_pre_event)}–{int(event.away_score_pre_event)} {event.away_team}")
    st.caption(
        f"{event_label(event)} · game state: {event.game_state} · event ID: `{selected_event}`"
    )
    if confidence:
        st.success("Recorded-pass association is spatially confident for this scene.")
    else:
        st.warning("Recorded-pass association is not confident; do not treat a nearest option as the known receiver.")
    if top.decision_status.startswith("inconclusive"):
        st.warning("The leading alternative changes under prespecified sensitivity checks.")
    else:
        st.info("The leading high-threat alternative is stable under the prespecified sensitivity checks.")

    metric_one, metric_two, metric_three = st.columns(3)
    metric_one.metric("Top-option completion probability", f"{top.p_success:.1%}")
    metric_two.metric("Top-option ΔxT", f"{top.xt_delta:.3f}")
    metric_three.metric("Frontier options", int(rows.model_estimated_frontier.sum()))

    png = _export(selected_event, utility, "png")
    left, right = st.columns((3, 2))
    with left:
        st.image(str(png), caption="Solid: recorded pass. Dashed: model-estimated alternatives.")
    with right:
        st.subheader("Candidate options")
        st.dataframe(_candidate_table(rows, utility), hide_index=True, width="stretch")
        st.subheader("Explainability")
        st.write(
            f"The selected view ranks option {int(top.candidate_index)} using `{utility}`. "
            f"It has {int(top.defenders_in_2_5m_corridor)} visible defender(s) in the straight-line corridor."
        )
        st.caption("360 actor markers are anonymous positional observations unless identity is grounded in event data.")

    png_data = png.read_bytes()
    svg = _export(selected_event, utility, "svg")
    export_one, export_two, export_three = st.columns(3)
    export_one.download_button("Download decision PNG", png_data, png.name, "image/png")
    export_two.download_button("Download decision SVG", svg.read_bytes(), svg.name, "image/svg+xml")
    export_three.button("Generate Tactical Clip", disabled=True, help="Available after Phase 6 animation export is implemented.")

    with st.expander("Evidence, provenance, and limits"):
        st.json(scene_for_event(selected_event, ranking_method=utility).as_dict()["provenance"])
        st.markdown(
            "The plot reconstructs one observed freeze frame. Completion and threat values are model estimates for visible candidate locations; they do not establish that an alternative pass would have been attempted or completed."
        )


if __name__ == "__main__":
    main()
