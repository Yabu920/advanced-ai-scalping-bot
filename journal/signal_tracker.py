"""JSONL signal tracker for full structured Stage 5 signal events."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from strategy.signal_types import ELIGIBLE, REJECTED, WATCHLIST


def _utc_now_iso() -> str:
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


class SignalTracker:
    """Append full signal decision events to JSONL."""

    def __init__(self, jsonl_path: str) -> None:
        self.jsonl_path = Path(jsonl_path)
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    def build_event(
        self,
        symbol: str,
        timeframe: str,
        signal: dict[str, Any],
        bias: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "event_time_utc": _utc_now_iso(),
            "event_type": "SIGNAL_DECISION",
            "symbol": symbol,
            "timeframe": timeframe,
            "bias": bias or {},
            "signal": signal,
            "future_outcome": {
                "checked": False,
                "status": "PENDING",
                "notes": "",
            },
        }

    def append_event(self, event: dict[str, Any]) -> None:
        with self.jsonl_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(to_json_safe(event), sort_keys=True) + "\n")

    def append_signals(
        self,
        signals: dict[str, Any],
        track_watchlist: bool = True,
        track_rejected: bool = True,
    ) -> int:
        count = 0
        for symbol, symbol_result in signals.items():
            bias = symbol_result.get("bias", {})
            for timeframe, signal in symbol_result.get("signals", {}).items():
                status = signal.get("status")
                should_track = (
                    status == ELIGIBLE
                    or (status == WATCHLIST and track_watchlist)
                    or (status == REJECTED and track_rejected)
                )
                if not should_track:
                    continue
                self.append_event(self.build_event(symbol, timeframe, signal, bias))
                count += 1
        return count
