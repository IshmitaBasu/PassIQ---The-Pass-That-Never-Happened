from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


def load_rankings(root: Path) -> pd.DataFrame:
    return pd.read_parquet(root / "data" / "gold" / "decision_rankings.parquet")


def event_catalog(root: Path, rankings: pd.DataFrame) -> pd.DataFrame:
    events = rankings[["match_id", "event_id", "decision_status"]].drop_duplicates()
    con = duckdb.connect(str(root / "data" / "gold" / "passiq.duckdb"), read_only=True)
    passes = con.execute(
        "select match_id, event_id, team, player_name, minute, second, home_team, away_team, "
        "home_score_pre_event, away_score_pre_event, game_state from fct_pass"
    ).df()
    con.close()
    return events.merge(passes, on=["match_id", "event_id"], how="left")


def match_label(row: pd.Series) -> str:
    return f"{row.home_team} v {row.away_team} ({int(row.match_id)})"


def event_label(row: pd.Series) -> str:
    player = row.player_name if pd.notna(row.player_name) else "Unknown player"
    return f"{int(row.minute):02}:{int(row.second):02} — {player} ({row.team})"
