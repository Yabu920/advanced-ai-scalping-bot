"""Trend and multi-timeframe bias analysis."""

from __future__ import annotations

from typing import Any

import pandas as pd


TREND_COLUMNS = ["close", "ema_20", "ema_50", "ema_200"]
TIMEFRAME_WEIGHTS = {"H1": 40, "M15": 30, "M5": 20, "M1": 10}


def _clean_float(value: Any) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _latest_closed_row(df: pd.DataFrame) -> pd.Series | None:
    if df.empty:
        return None
    if "is_closed_candle" in df.columns:
        closed = df[df["is_closed_candle"] == True]
        if closed.empty:
            return None
        return closed.iloc[-1]
    if len(df) < 2:
        return None
    return df.iloc[-2]


def analyze_trend(df: pd.DataFrame) -> dict[str, Any]:
    missing = [column for column in TREND_COLUMNS if column not in df.columns]
    if missing:
        return {
            "trend": "neutral",
            "strength": "weak",
            "reason": f"Missing trend columns: {', '.join(missing)}",
            "close": None,
            "ema_20": None,
            "ema_50": None,
            "ema_200": None,
        }

    latest = _latest_closed_row(df)
    if latest is None:
        return {
            "trend": "neutral",
            "strength": "weak",
            "reason": "Not enough closed candle data for trend analysis.",
            "close": None,
            "ema_20": None,
            "ema_50": None,
            "ema_200": None,
        }

    close = _clean_float(latest["close"])
    ema_20 = _clean_float(latest["ema_20"])
    ema_50 = _clean_float(latest["ema_50"])
    ema_200 = _clean_float(latest["ema_200"])

    if None in [close, ema_20, ema_50, ema_200]:
        return {
            "trend": "neutral",
            "strength": "weak",
            "reason": "Trend values contain missing data.",
            "close": close,
            "ema_20": ema_20,
            "ema_50": ema_50,
            "ema_200": ema_200,
        }

    if close > ema_20 > ema_50 > ema_200:
        trend = "bullish"
        strength = "strong"
        reason = "Close and EMA20/EMA50/EMA200 are bullish aligned."
    elif close < ema_20 < ema_50 < ema_200:
        trend = "bearish"
        strength = "strong"
        reason = "Close and EMA20/EMA50/EMA200 are bearish aligned."
    elif close > ema_20 > ema_50:
        trend = "bullish"
        strength = "medium"
        reason = "Close is above EMA20 and EMA50, but EMA200 is not fully aligned."
    elif close < ema_20 < ema_50:
        trend = "bearish"
        strength = "medium"
        reason = "Close is below EMA20 and EMA50, but EMA200 is not fully aligned."
    else:
        trend = "neutral"
        strength = "weak"
        reason = "EMA structure is not clearly aligned."

    return {
        "trend": trend,
        "strength": strength,
        "reason": reason,
        "close": close,
        "ema_20": ema_20,
        "ema_50": ema_50,
        "ema_200": ema_200,
    }


def analyze_multi_timeframe_bias(symbol_data: dict[str, pd.DataFrame]) -> dict[str, Any]:
    timeframe_trends = {
        timeframe: analyze_trend(df)
        for timeframe, df in symbol_data.items()
    }

    bullish_score = 0
    bearish_score = 0
    neutral_score = 0
    for timeframe, result in timeframe_trends.items():
        weight = TIMEFRAME_WEIGHTS.get(timeframe.upper(), 0)
        if result["trend"] == "bullish":
            bullish_score += weight
        elif result["trend"] == "bearish":
            bearish_score += weight
        else:
            neutral_score += weight

    h1_trend = timeframe_trends.get("H1", {}).get("trend")
    m15_trend = timeframe_trends.get("M15", {}).get("trend")

    if h1_trend == "bullish" and m15_trend == "bullish":
        bias = "bullish"
        confidence = bullish_score
        reason = "H1 and M15 bullish."
    elif h1_trend == "bearish" and m15_trend == "bearish":
        bias = "bearish"
        confidence = bearish_score
        reason = "H1 and M15 bearish."
    elif bullish_score > 0 and bearish_score > 0:
        bias = "mixed"
        confidence = max(bullish_score, bearish_score)
        reason = "Timeframes conflict between bullish and bearish trends."
    elif neutral_score >= max(bullish_score, bearish_score):
        bias = "neutral"
        confidence = neutral_score
        reason = "Most timeframe weight is neutral."
    elif bullish_score > bearish_score:
        bias = "bullish"
        confidence = bullish_score
        reason = "Bullish timeframe weight is dominant."
    else:
        bias = "bearish"
        confidence = bearish_score
        reason = "Bearish timeframe weight is dominant."

    return {
        "bias": bias,
        "confidence": int(min(confidence, 100)),
        "timeframe_trends": timeframe_trends,
        "reason": reason,
    }
