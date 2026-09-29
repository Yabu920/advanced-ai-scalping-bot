"""Volatility analysis helpers."""

from __future__ import annotations

from typing import Any

import pandas as pd


def analyze_volatility(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty or "atr_14" not in df.columns or "candle_range" not in df.columns:
        return {
            "volatility": "unknown",
            "atr_14": None,
            "average_atr_50": None,
            "atr_ratio": None,
            "reason": "Missing ATR or candle range data.",
        }

    if "is_closed_candle" in df.columns:
        closed = df[df["is_closed_candle"] == True]
    else:
        closed = df.iloc[:-1]

    closed = closed.dropna(subset=["atr_14"])
    if len(closed) < 50:
        return {
            "volatility": "unknown",
            "atr_14": None,
            "average_atr_50": None,
            "atr_ratio": None,
            "reason": "Not enough closed ATR data.",
        }

    latest_atr = float(closed["atr_14"].iloc[-1])
    average_atr_50 = float(closed["atr_14"].tail(50).mean())
    if average_atr_50 <= 0:
        return {
            "volatility": "unknown",
            "atr_14": latest_atr,
            "average_atr_50": average_atr_50,
            "atr_ratio": None,
            "reason": "Average ATR is not usable.",
        }

    atr_ratio = latest_atr / average_atr_50
    if atr_ratio < 0.70:
        volatility = "low"
    elif atr_ratio <= 1.40:
        volatility = "normal"
    elif atr_ratio <= 2.00:
        volatility = "high"
    else:
        volatility = "extreme"

    return {
        "volatility": volatility,
        "atr_14": latest_atr,
        "average_atr_50": average_atr_50,
        "atr_ratio": atr_ratio,
        "reason": f"ATR ratio is {atr_ratio:.2f}.",
    }
