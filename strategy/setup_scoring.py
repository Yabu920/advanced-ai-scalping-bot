"""Setup scoring for Stage 4 signal candidates."""

from __future__ import annotations

from typing import Any

import pandas as pd

from strategy.signal_rules import (
    check_ema_alignment,
    check_regime_tradable,
    check_rsi_confirmation,
    determine_direction_from_bias,
    get_latest_closed_row,
)
from strategy.signal_types import (
    BAD_SPREAD,
    ELIGIBLE,
    INSUFFICIENT_DATA,
    LOW_VOLATILITY,
    MIXED_BIAS,
    NEUTRAL_BIAS,
    NO_TRADE,
    REJECTED,
    WATCHLIST,
)


HARD_REJECTIONS = {BAD_SPREAD, LOW_VOLATILITY, MIXED_BIAS, NEUTRAL_BIAS, INSUFFICIENT_DATA}


def _add_condition(target: list[str], text: str) -> None:
    if text not in target:
        target.append(text)


def _add_rejection(target: list[str], reason: str | None) -> None:
    if reason and reason not in target:
        target.append(reason)


def _bias_rejection_reason(bias: str) -> str:
    if bias == "mixed":
        return MIXED_BIAS
    if bias == "neutral":
        return NEUTRAL_BIAS
    return INSUFFICIENT_DATA


def score_setup(
    symbol: str,
    timeframe: str,
    df: pd.DataFrame,
    timeframe_analysis: dict[str, Any],
    mtf_bias: dict[str, Any],
    settings: Any,
) -> dict[str, Any]:
    passed_conditions: list[str] = []
    failed_conditions: list[str] = []
    rejection_reasons: list[str] = []
    details: dict[str, Any] = {}
    score = 0

    direction_result = determine_direction_from_bias(
        mtf_bias,
        getattr(settings, "allow_mixed_bias", False),
    )
    direction = direction_result["direction"]
    details["bias_direction"] = direction_result
    details["timeframe_analysis"] = timeframe_analysis

    if direction_result["allowed"] and direction != NO_TRADE:
        score += 25
        _add_condition(passed_conditions, direction_result["reason"])
    else:
        _add_condition(failed_conditions, direction_result["reason"])
        _add_rejection(rejection_reasons, _bias_rejection_reason(mtf_bias.get("bias", "neutral")))

    confidence = int(mtf_bias.get("confidence", 0) or 0)
    if confidence >= 80:
        score += 15
        _add_condition(passed_conditions, "Bias confidence is strong.")
    elif confidence >= 60:
        score += 10
        _add_condition(passed_conditions, "Bias confidence is medium.")
    elif confidence >= 40:
        score += 5
        _add_condition(passed_conditions, "Bias confidence is weak but present.")
    else:
        _add_condition(failed_conditions, "Bias confidence is too low.")

    regime_check = check_regime_tradable(timeframe_analysis.get("regime", {}))
    details["regime_check"] = regime_check
    score += int(regime_check.get("score", 0))
    if regime_check["passed"]:
        _add_condition(passed_conditions, regime_check["reason"])
    else:
        _add_condition(failed_conditions, regime_check["reason"])
        _add_rejection(rejection_reasons, regime_check.get("rejection_reason"))

    latest = get_latest_closed_row(df)
    if latest is None:
        _add_condition(failed_conditions, "Insufficient closed candle data.")
        _add_rejection(rejection_reasons, INSUFFICIENT_DATA)
    elif direction != NO_TRADE:
        details["latest_candle"] = latest.to_dict()
        ema_check = check_ema_alignment(latest, direction)
        rsi_check = check_rsi_confirmation(latest, direction)
        details["ema_check"] = ema_check
        details["rsi_check"] = rsi_check
        score += int(ema_check.get("score", 0))
        score += int(rsi_check.get("score", 0))

        if ema_check["passed"]:
            _add_condition(passed_conditions, ema_check["reason"])
        else:
            _add_condition(failed_conditions, ema_check["reason"])

        if rsi_check["passed"]:
            _add_condition(passed_conditions, rsi_check["reason"])
        else:
            _add_condition(failed_conditions, rsi_check["reason"])

    volatility = timeframe_analysis.get("volatility", {}).get("volatility")
    if volatility in {"normal", "high"}:
        score += 5
        _add_condition(passed_conditions, f"Volatility is {volatility}.")
    elif volatility in {"low", "extreme"}:
        _add_condition(failed_conditions, f"Volatility is {volatility}.")
    else:
        _add_condition(failed_conditions, "Volatility is unknown.")

    score = max(0, min(score, 100))
    has_hard_rejection = any(reason in HARD_REJECTIONS for reason in rejection_reasons)

    if has_hard_rejection or direction == NO_TRADE:
        status = REJECTED
    elif score >= settings.min_signal_score:
        status = ELIGIBLE
    elif score >= settings.watchlist_score:
        status = WATCHLIST
    else:
        status = REJECTED

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "direction": direction,
        "status": status,
        "score": score,
        "max_score": 100,
        "passed_conditions": passed_conditions,
        "failed_conditions": failed_conditions,
        "rejection_reasons": rejection_reasons,
        "details": details,
    }
