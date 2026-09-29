"""Outcome tracker for saved signal decision events."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pandas as pd

from learning.signal_outcome import calculate_future_outcome, classify_signal_learning_result


OUTCOME_REPORT_FIELDS = [
    "event_time_utc",
    "symbol",
    "timeframe",
    "direction",
    "status",
    "score",
    "rejection_reasons",
    "outcome_label",
    "learning_label",
    "mistake_category",
    "first_hit",
    "future_candles_checked",
    "lesson",
]


def _join_list(value: Any) -> str:
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    return "" if value is None else str(value)


class OutcomeTracker:
    """Evaluate recent signal events and append outcome rows."""

    def __init__(self, signal_history_path: str, outcome_report_path: str) -> None:
        self.signal_history_path = Path(signal_history_path)
        self.outcome_report_path = Path(outcome_report_path)
        self.outcome_report_path.parent.mkdir(parents=True, exist_ok=True)

    def load_recent_signal_events(self, max_events: int) -> list[dict[str, Any]]:
        if not self.signal_history_path.exists():
            return []

        events: list[dict[str, Any]] = []
        with self.signal_history_path.open("r", encoding="utf-8") as file:
            for line in file:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("event_type") != "SIGNAL_DECISION":
                    continue
                future_outcome = event.get("future_outcome", {})
                if isinstance(future_outcome, dict) and future_outcome.get("checked") is True:
                    continue
                events.append(event)

        return events[-max_events:]

    def evaluate_event(
        self,
        event: dict[str, Any],
        market_data: dict[str, dict[str, pd.DataFrame]],
        settings: Any,
    ) -> dict[str, Any]:
        symbol = event.get("symbol")
        timeframe = event.get("timeframe")
        signal = event.get("signal", {})
        df = market_data.get(symbol, {}).get(timeframe, pd.DataFrame())

        outcome = calculate_future_outcome(
            signal,
            df,
            settings.outcome_lookahead_candles,
            settings.outcome_min_move_atr,
            settings.outcome_adverse_move_atr,
        )
        learning = classify_signal_learning_result(signal, outcome)

        return {
            "event_time_utc": event.get("event_time_utc"),
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": signal.get("direction"),
            "status": signal.get("status"),
            "score": signal.get("score"),
            "rejection_reasons": _join_list(signal.get("rejection_reasons")),
            "outcome_label": outcome.get("outcome_label"),
            "learning_label": learning.get("learning_label"),
            "mistake_category": learning.get("mistake_category"),
            "first_hit": outcome.get("first_hit"),
            "future_candles_checked": outcome.get("future_candles_checked"),
            "lesson": learning.get("lesson"),
        }

    def evaluate_recent_events(
        self,
        market_data: dict[str, dict[str, pd.DataFrame]],
        settings: Any,
    ) -> list[dict[str, Any]]:
        events = self.load_recent_signal_events(settings.outcome_max_events_to_check)
        return [self.evaluate_event(event, market_data, settings) for event in events]

    def append_outcome_report(self, results: list[dict[str, Any]]) -> int:
        if not results:
            return 0

        file_exists = self.outcome_report_path.exists() and self.outcome_report_path.stat().st_size > 0
        with self.outcome_report_path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=OUTCOME_REPORT_FIELDS, extrasaction="ignore")
            if not file_exists:
                writer.writeheader()
            for result in results:
                writer.writerow({field: result.get(field) for field in OUTCOME_REPORT_FIELDS})
        return len(results)
