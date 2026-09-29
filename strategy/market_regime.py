"""Market regime classification."""

from __future__ import annotations

from typing import Any


def classify_market_regime(
    trend_result: dict[str, Any],
    volatility_result: dict[str, Any],
    spread_result: dict[str, Any],
) -> dict[str, Any]:
    spread_quality = spread_result.get("spread_quality")
    volatility = volatility_result.get("volatility")
    trend = trend_result.get("trend")

    if spread_quality == "high":
        return {
            "regime": "BAD_SPREAD",
            "tradable": False,
            "reason": "Spread is too high for Stage 3 conditions.",
        }
    if volatility == "unknown" or trend is None:
        return {
            "regime": "UNKNOWN",
            "tradable": False,
            "reason": "Not enough data to classify the market regime.",
        }
    if volatility == "extreme":
        return {
            "regime": "HIGH_VOLATILITY",
            "tradable": False,
            "reason": "Volatility is extreme.",
        }
    if volatility == "low":
        return {
            "regime": "LOW_VOLATILITY",
            "tradable": False,
            "reason": "Volatility is too low.",
        }
    if trend in {"bullish", "bearish"} and volatility in {"normal", "high"} and spread_quality in {"good", "acceptable"}:
        return {
            "regime": "TRENDING",
            "tradable": True,
            "reason": "Trend, volatility, and spread are acceptable.",
        }
    if trend == "neutral" and volatility == "normal":
        return {
            "regime": "RANGING",
            "tradable": False,
            "reason": "Trend is neutral with normal volatility.",
        }
    if trend == "neutral" and volatility == "high":
        return {
            "regime": "CHOPPY",
            "tradable": False,
            "reason": "Trend is neutral with high volatility.",
        }

    return {
        "regime": "UNKNOWN",
        "tradable": False,
        "reason": "Market conditions are unclear.",
    }
