"""Persistence for paper trade simulation."""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from paper.paper_trade import (
    CLOSED_MANUAL,
    CLOSED_SL,
    CLOSED_TP,
    EXPIRED,
    INVALID,
    OPEN,
)

CSV_FIELDS = [
    "paper_trade_id",
    "created_time_utc",
    "opened_candle_time",
    "signal_candle_time",
    "last_evaluated_candle_time",
    "symbol",
    "timeframe",
    "direction",
    "source",
    "status",
    "entry_price",
    "stop_loss",
    "take_profit",
    "lot_size",
    "risk_amount",
    "risk_percent",
    "rr_ratio",
    "spread_points_at_entry",
    "spread_cost_amount",
    "spread_cost_known",
    "signal_score",
    "signal_status",
    "paper_experiment_name",
    "paper_filters_enabled",
    "paper_filter_summary",
    "close_time_utc",
    "close_price",
    "gross_pnl_amount",
    "gross_pnl_r",
    "total_cost_amount",
    "pnl_amount",
    "pnl_r",
    "pnl_basis",
    "close_reason",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): to_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [to_json_safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


class PaperJournal:
    """Append paper trades and keep latest open trade snapshots."""

    def __init__(self, csv_path: str, jsonl_path: str, snapshot_path: str) -> None:
        self.csv_path = Path(csv_path)
        self.jsonl_path = Path(jsonl_path)
        self.snapshot_path = Path(snapshot_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    def load_open_trades(self) -> list[dict]:
        return self.get_current_open_trades()

    def load_all_trade_events(self) -> list[dict]:
        if not self.jsonl_path.exists():
            return []
        events: list[dict] = []
        with self.jsonl_path.open("r", encoding="utf-8") as file:
            for line in file:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(event.get("paper_trade"), dict):
                    events.append(event)
        return events

    def reconstruct_latest_trade_states(self) -> dict[str, dict]:
        latest_by_id: dict[str, dict] = {}
        for event in self.load_all_trade_events():
            trade = event.get("paper_trade", {})
            trade_id = trade.get("paper_trade_id")
            if trade_id:
                latest_by_id[trade_id] = trade
        return latest_by_id

    def get_current_open_trades(self) -> list[dict]:
        return [trade for trade in self.reconstruct_latest_trade_states().values() if trade.get("status") == OPEN]

    def get_closed_trades(self) -> list[dict]:
        closed_statuses = {CLOSED_TP, CLOSED_SL, CLOSED_MANUAL, EXPIRED, INVALID}
        return [trade for trade in self.reconstruct_latest_trade_states().values() if trade.get("status") in closed_statuses]

    def append_trades(self, trades: list[dict]) -> int:
        if not trades:
            return 0
        file_exists = self.csv_path.exists() and self.csv_path.stat().st_size > 0
        with self.csv_path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_FIELDS, extrasaction="ignore")
            if not file_exists:
                writer.writeheader()
            for trade in trades:
                writer.writerow({field: to_json_safe(trade.get(field)) for field in CSV_FIELDS})
        self.append_trade_events(trades, "PAPER_TRADE_OPENED")
        return len(trades)

    def append_trade_events(self, trades: list[dict], event_type: str) -> int:
        if not trades:
            return 0
        with self.jsonl_path.open("a", encoding="utf-8") as file:
            for trade in trades:
                event = {
                    "event_time_utc": _utc_now(),
                    "event_type": event_type,
                    "paper_trade": trade,
                }
                file.write(json.dumps(to_json_safe(event), sort_keys=True) + "\n")
        return len(trades)

    def save_snapshot(self, trades: list[dict]) -> None:
        open_trades = [trade for trade in trades if trade.get("status") == OPEN]
        self.snapshot_path.write_text(json.dumps(to_json_safe(open_trades), indent=2), encoding="utf-8")

    def save_execution_output(self, output: dict, output_path: str) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(to_json_safe(output), indent=2), encoding="utf-8")

    def append_closed_trades_csv(self, closed_trades: list[dict], closed_csv_path: str) -> int:
        if not closed_trades:
            return 0
        path = Path(closed_csv_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        existing_ids: set[str] = set()
        if path.exists() and path.stat().st_size > 0:
            with path.open("r", newline="", encoding="utf-8") as file:
                for row in csv.DictReader(file):
                    if row.get("paper_trade_id"):
                        existing_ids.add(row["paper_trade_id"])

        new_rows = [trade for trade in closed_trades if trade.get("paper_trade_id") not in existing_ids]
        if not new_rows:
            return 0
        file_exists = path.exists() and path.stat().st_size > 0
        with path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_FIELDS, extrasaction="ignore")
            if not file_exists:
                writer.writeheader()
            for trade in new_rows:
                writer.writerow({field: to_json_safe(trade.get(field)) for field in CSV_FIELDS})
        return len(new_rows)

    def save_status_report(self, report: dict, path: str) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(to_json_safe(report), indent=2), encoding="utf-8")
