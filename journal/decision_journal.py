"""CSV decision journal for Stage 5 signal tracking."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


FIELDNAMES = [
    "journal_time_utc",
    "symbol",
    "timeframe",
    "direction",
    "status",
    "score",
    "max_score",
    "bias",
    "bias_confidence",
    "rejection_reasons",
    "passed_conditions",
    "failed_conditions",
    "latest_time",
    "latest_close",
    "trend",
    "trend_strength",
    "regime",
    "tradable",
    "spread_quality",
    "spread_points",
    "volatility",
    "atr_14",
    "rsi_14",
    "ema_20",
    "ema_50",
    "ema_200",
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _join_list(value: Any) -> str:
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    return "" if value is None else str(value)


def _format_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def _nested(source: dict[str, Any], *keys: str) -> Any:
    current: Any = source
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


class DecisionJournal:
    """Append flat signal decisions to a CSV file."""

    def __init__(self, csv_path: str) -> None:
        self.csv_path = Path(csv_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)

    def flatten_signal_record(
        self,
        symbol: str,
        timeframe: str,
        signal: dict[str, Any],
        bias: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        bias = bias or {}
        details = signal.get("details", {})

        return {
            "journal_time_utc": _utc_now_iso(),
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": signal.get("direction"),
            "status": signal.get("status"),
            "score": signal.get("score"),
            "max_score": signal.get("max_score"),
            "bias": bias.get("bias"),
            "bias_confidence": bias.get("confidence"),
            "rejection_reasons": _join_list(signal.get("rejection_reasons")),
            "passed_conditions": _join_list(signal.get("passed_conditions")),
            "failed_conditions": _join_list(signal.get("failed_conditions")),
            "latest_time": _format_value(_nested(details, "latest_candle", "time")),
            "latest_close": _format_value(_nested(details, "latest_candle", "close")),
            "trend": _nested(details, "timeframe_analysis", "trend", "trend"),
            "trend_strength": _nested(details, "timeframe_analysis", "trend", "strength"),
            "regime": _nested(details, "timeframe_analysis", "regime", "regime"),
            "tradable": _nested(details, "timeframe_analysis", "regime", "tradable"),
            "spread_quality": _nested(details, "timeframe_analysis", "spread", "spread_quality"),
            "spread_points": _format_value(_nested(details, "timeframe_analysis", "spread", "spread_points")),
            "volatility": _nested(details, "timeframe_analysis", "volatility", "volatility"),
            "atr_14": _format_value(_nested(details, "timeframe_analysis", "volatility", "atr_14")),
            "rsi_14": _format_value(_nested(details, "latest_candle", "rsi_14")),
            "ema_20": _format_value(_nested(details, "latest_candle", "ema_20")),
            "ema_50": _format_value(_nested(details, "latest_candle", "ema_50")),
            "ema_200": _format_value(_nested(details, "latest_candle", "ema_200")),
        }

    def append_record(self, record: dict[str, Any]) -> None:
        file_exists = self.csv_path.exists() and self.csv_path.stat().st_size > 0
        with self.csv_path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDNAMES, extrasaction="ignore")
            if not file_exists:
                writer.writeheader()
            writer.writerow({field: record.get(field) for field in FIELDNAMES})

    def append_signals(self, signals: dict[str, Any]) -> int:
        count = 0
        for symbol, symbol_result in signals.items():
            bias = symbol_result.get("bias", {})
            for timeframe, signal in symbol_result.get("signals", {}).items():
                record = self.flatten_signal_record(symbol, timeframe, signal, bias)
                self.append_record(record)
                count += 1
        return count
