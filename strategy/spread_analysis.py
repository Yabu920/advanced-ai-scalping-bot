"""Spread quality analysis helpers."""

from __future__ import annotations

from typing import Any


def analyze_spread(symbol: str, spread_points: float | None, atr_value: float | None) -> dict[str, Any]:
    if spread_points is None:
        return {
            "spread_quality": "unknown",
            "spread_points": None,
            "atr_value": atr_value,
            "reason": "Spread is unavailable.",
        }

    symbol_upper = symbol.upper()
    # These thresholds are broker-dependent and will be tuned later using live data.
    if "XAUUSD" in symbol_upper:
        good_threshold = 80
        acceptable_threshold = 150
    elif "EURUSD" in symbol_upper or "GBPUSD" in symbol_upper:
        good_threshold = 20
        acceptable_threshold = 35
    else:
        good_threshold = 20
        acceptable_threshold = 35

    if spread_points <= good_threshold:
        quality = "good"
        reason = "Spread is within the good threshold."
    elif spread_points <= acceptable_threshold:
        quality = "acceptable"
        reason = "Spread is acceptable but not ideal."
    else:
        quality = "high"
        reason = "Spread is above the Stage 3 threshold."

    return {
        "spread_quality": quality,
        "spread_points": float(spread_points),
        "atr_value": atr_value,
        "reason": reason,
    }
