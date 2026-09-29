"""Pure signal rule helpers for Stage 4 setup scoring."""

from __future__ import annotations

from typing import Any

import pandas as pd

from strategy.signal_types import (
    BAD_SPREAD,
    BUY,
    EMA_NOT_ALIGNED,
    EXTREME_VOLATILITY,
    LOW_VOLATILITY,
    MIXED_BIAS,
    NEUTRAL_BIAS,
    NO_TRADE,
    RSI_NOT_CONFIRMED,
    SELL,
    TIMEFRAME_NOT_TRADABLE,
)


def determine_direction_from_bias(
    bias_result: dict[str, Any],
    allow_mixed_bias: bool = False,
) -> dict[str, Any]:
    bias = bias_result.get("bias", "neutral")
    if bias == "bullish":
        return {"direction": BUY, "allowed": True, "reason": "Bullish bias supports BUY."}
    if bias == "bearish":
        return {"direction": SELL, "allowed": True, "reason": "Bearish bias supports SELL."}
    if bias == "mixed":
        if allow_mixed_bias:
            return {
                "direction": NO_TRADE,
                "allowed": True,
                "reason": "Mixed bias is allowed, but no clear direction is selected in Stage 4.",
            }
        return {"direction": NO_TRADE, "allowed": False, "reason": "Mixed bias blocks signal candidates."}
    return {"direction": NO_TRADE, "allowed": False, "reason": "Neutral bias blocks signal candidates."}


def check_ema_alignment(row: pd.Series, direction: str) -> dict[str, Any]:
    close = row.get("close")
    ema_20 = row.get("ema_20")
    ema_50 = row.get("ema_50")
    if pd.isna(close) or pd.isna(ema_20) or pd.isna(ema_50):
        return {"passed": False, "score": 0, "reason": "EMA data is missing.", "rejection_reason": EMA_NOT_ALIGNED}

    if direction == BUY:
        if close > ema_20 and ema_20 >= ema_50:
            return {"passed": True, "score": 20, "reason": "BUY EMA alignment is strong."}
        if close > ema_20:
            return {"passed": True, "score": 10, "reason": "BUY EMA alignment is partial."}
    elif direction == SELL:
        if close < ema_20 and ema_20 <= ema_50:
            return {"passed": True, "score": 20, "reason": "SELL EMA alignment is strong."}
        if close < ema_20:
            return {"passed": True, "score": 10, "reason": "SELL EMA alignment is partial."}

    return {"passed": False, "score": 0, "reason": "EMA alignment did not confirm direction.", "rejection_reason": EMA_NOT_ALIGNED}


def check_rsi_confirmation(row: pd.Series, direction: str) -> dict[str, Any]:
    rsi = row.get("rsi_14")
    if pd.isna(rsi):
        return {"passed": False, "score": 0, "reason": "RSI data is missing.", "rejection_reason": RSI_NOT_CONFIRMED}

    if direction == BUY:
        if rsi >= 52:
            return {"passed": True, "score": 15, "reason": "RSI strongly confirms BUY."}
        if 48 <= rsi < 52:
            return {"passed": True, "score": 7, "reason": "RSI weakly confirms BUY."}
    elif direction == SELL:
        if rsi <= 48:
            return {"passed": True, "score": 15, "reason": "RSI strongly confirms SELL."}
        if 48 < rsi <= 52:
            return {"passed": True, "score": 7, "reason": "RSI weakly confirms SELL."}

    return {"passed": False, "score": 0, "reason": "RSI did not confirm direction.", "rejection_reason": RSI_NOT_CONFIRMED}


def check_regime_tradable(regime_result: dict[str, Any]) -> dict[str, Any]:
    regime = regime_result.get("regime", "UNKNOWN")
    tradable = bool(regime_result.get("tradable"))
    if not tradable:
        if regime == "BAD_SPREAD":
            rejection = BAD_SPREAD
        elif regime == "LOW_VOLATILITY":
            rejection = LOW_VOLATILITY
        elif regime in {"HIGH_VOLATILITY", "EXTREME"}:
            rejection = EXTREME_VOLATILITY
        else:
            rejection = TIMEFRAME_NOT_TRADABLE
        return {
            "passed": False,
            "score": 0,
            "reason": f"Regime {regime} is not tradable.",
            "rejection_reason": rejection,
        }

    if regime == "TRENDING":
        score = 20
    elif regime == "RANGING":
        score = 10
    else:
        score = 0

    return {
        "passed": score > 0,
        "score": score,
        "reason": f"Regime {regime} is tradable.",
        "rejection_reason": None,
    }


def get_latest_closed_row(df: pd.DataFrame) -> pd.Series | None:
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
