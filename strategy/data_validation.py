"""Validation helpers for collected OHLC market data."""

from __future__ import annotations

from typing import Any

import pandas as pd


REQUIRED_OHLC_COLUMNS = [
    "time",
    "open",
    "high",
    "low",
    "close",
    "tick_volume",
    "spread",
]


def validate_ohlc_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    issues: list[str] = []
    rows = len(df)
    result: dict[str, Any] = {
        "valid": False,
        "issues": issues,
        "rows": rows,
        "start_time": None,
        "end_time": None,
    }

    if df.empty:
        issues.append("empty dataframe")
        return result

    missing = [column for column in REQUIRED_OHLC_COLUMNS if column not in df.columns]
    if missing:
        issues.append(f"missing columns: {', '.join(missing)}")

    if "is_closed_candle" not in df.columns:
        issues.append("missing is_closed_candle")

    if "time" in df.columns:
        result["start_time"] = df["time"].iloc[0]
        result["end_time"] = df["time"].iloc[-1]
        if not df["time"].is_monotonic_increasing:
            issues.append("time not sorted ascending")
        if df["time"].duplicated().any():
            issues.append("duplicate time")
    else:
        issues.append("latest candle missing")

    if rows < 50:
        issues.append("not enough rows")

    if {"open", "high", "low", "close"}.issubset(df.columns):
        if (df["high"] < df["low"]).any():
            issues.append("high below low")
        if ((df["high"] < df["open"]) | (df["high"] < df["close"])).any():
            issues.append("high below open or close")
        if ((df["low"] > df["open"]) | (df["low"] > df["close"])).any():
            issues.append("low above open or close")

    result["valid"] = not issues
    return result


def validate_multi_symbol_data(
    data: dict[str, dict[str, pd.DataFrame]],
) -> dict[str, dict[str, dict[str, Any]]]:
    validation: dict[str, dict[str, dict[str, Any]]] = {}
    for symbol, timeframe_data in data.items():
        validation[symbol] = {}
        for timeframe, df in timeframe_data.items():
            validation[symbol][timeframe] = validate_ohlc_dataframe(df)
    return validation
