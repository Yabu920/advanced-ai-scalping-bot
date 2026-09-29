"""Market diagnostics snapshot helpers."""

from __future__ import annotations

from typing import Any

import pandas as pd


SNAPSHOT_COLUMNS = ["close", "ema_20", "ema_50", "ema_200", "rsi_14", "atr_14"]


def _clean_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def build_market_snapshot(df: pd.DataFrame) -> dict[str, Any]:
    """Build a diagnostic snapshot from the latest available closed candle."""
    if df.empty:
        return {"enough_data": False, "reason": "No candle data available."}
    if len(df) < 2:
        return {
            "enough_data": False,
            "reason": "At least two candles are required to avoid using a forming candle.",
        }

    missing = [column for column in SNAPSHOT_COLUMNS if column not in df.columns]
    if missing:
        return {
            "enough_data": False,
            "reason": f"Missing indicator columns: {missing}",
        }

    latest = df.iloc[-2]
    close = _clean_value(latest.get("close"))
    ema_20 = _clean_value(latest.get("ema_20"))
    ema_50 = _clean_value(latest.get("ema_50"))

    trend_hint = "neutral"
    if close is not None and ema_20 is not None and ema_50 is not None:
        if close > ema_20 > ema_50:
            trend_hint = "bullish"
        elif close < ema_20 < ema_50:
            trend_hint = "bearish"

    return {
        "enough_data": True,
        "symbol": _clean_value(latest.get("symbol")),
        "timeframe": _clean_value(latest.get("timeframe")),
        "latest_time": _clean_value(latest.get("time")),
        "latest_close": close,
        "ema_20": ema_20,
        "ema_50": ema_50,
        "ema_200": _clean_value(latest.get("ema_200")),
        "rsi_14": _clean_value(latest.get("rsi_14")),
        "atr_14": _clean_value(latest.get("atr_14")),
        "trend_hint": trend_hint,
    }
