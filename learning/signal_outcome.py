"""Pure signal outcome calculations for Stage 6."""

from __future__ import annotations

from typing import Any

import pandas as pd

from learning.outcome_types import (
    ADVERSE_MOVE,
    BAD_ELIGIBLE_SIGNAL,
    BAD_MARKET_CONDITION,
    BOTH_HIT,
    CORRECT_REJECTION,
    CORRECT_WATCHLIST,
    FAVORABLE_MOVE,
    FILTER_PROTECTED_ACCOUNT,
    FILTER_TOO_STRICT,
    INSUFFICIENT_FUTURE_DATA,
    MISSED_GOOD_TRADE,
    NO_CLEAR_MOVE,
    UNCLEAR,
    UNKNOWN,
    UNKNOWN_DIRECTION,
)
from strategy.signal_types import BUY, ELIGIBLE, REJECTED, SELL, WATCHLIST


def direction_to_sign(direction: str) -> int:
    if direction == BUY:
        return 1
    if direction == SELL:
        return -1
    return 0


def _nested(source: dict[str, Any], *keys: str) -> Any:
    current: Any = source
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _signal_value(signal: dict[str, Any], key: str) -> Any:
    if key in signal:
        return signal.get(key)
    latest = _nested(signal, "details", "latest_candle", key)
    if latest is not None:
        return latest
    if key == "atr_14":
        return _nested(signal, "details", "timeframe_analysis", "volatility", "atr_14")
    return None


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_time(value: Any) -> pd.Timestamp | None:
    if value is None:
        return None
    try:
        return pd.Timestamp(value)
    except (TypeError, ValueError):
        return None


def _base_outcome(label: str, notes: str, lookahead_candles: int) -> dict[str, Any]:
    return {
        "outcome_label": label,
        "entry_reference": None,
        "atr_reference": None,
        "favorable_target": None,
        "adverse_target": None,
        "lookahead_candles": lookahead_candles,
        "future_candles_checked": 0,
        "max_favorable_move": 0.0,
        "max_adverse_move": 0.0,
        "first_hit": "UNKNOWN",
        "notes": notes,
    }


def calculate_future_outcome(
    signal: dict[str, Any],
    future_df: pd.DataFrame,
    lookahead_candles: int,
    favorable_atr: float,
    adverse_atr: float,
) -> dict[str, Any]:
    direction = signal.get("direction")
    sign = direction_to_sign(direction)
    if sign == 0:
        return _base_outcome(UNKNOWN_DIRECTION, "Signal direction is not BUY or SELL.", lookahead_candles)

    entry = _safe_float(_signal_value(signal, "close") or _signal_value(signal, "latest_close"))
    atr = _safe_float(_signal_value(signal, "atr_14"))
    signal_time = _safe_time(_signal_value(signal, "time") or _signal_value(signal, "latest_time"))
    if entry is None or atr is None or atr <= 0 or signal_time is None:
        return _base_outcome(INSUFFICIENT_FUTURE_DATA, "Signal is missing entry, ATR, or time reference.", lookahead_candles)

    if future_df.empty or "time" not in future_df.columns:
        result = _base_outcome(INSUFFICIENT_FUTURE_DATA, "No future candle data is available.", lookahead_candles)
        result.update({"entry_reference": entry, "atr_reference": atr})
        return result

    df = future_df.copy()
    if "is_closed_candle" in df.columns:
        df = df[df["is_closed_candle"] == True]
    df = df[df["time"] > signal_time].sort_values("time").head(lookahead_candles)
    if len(df) < lookahead_candles:
        label = INSUFFICIENT_FUTURE_DATA
        notes = "Not enough future closed candles are available yet."
    else:
        label = NO_CLEAR_MOVE
        notes = "No favorable or adverse threshold was reached."

    favorable_target = entry + atr * favorable_atr if sign == 1 else entry - atr * favorable_atr
    adverse_target = entry - atr * adverse_atr if sign == 1 else entry + atr * adverse_atr

    favorable_hits: list[int] = []
    adverse_hits: list[int] = []
    max_favorable = 0.0
    max_adverse = 0.0

    for position, (_, row) in enumerate(df.iterrows(), start=1):
        high = float(row["high"])
        low = float(row["low"])
        if sign == 1:
            favorable_move = high - entry
            adverse_move = entry - low
            favorable_hit = high >= favorable_target
            adverse_hit = low <= adverse_target
        else:
            favorable_move = entry - low
            adverse_move = high - entry
            favorable_hit = low <= favorable_target
            adverse_hit = high >= adverse_target

        max_favorable = max(max_favorable, favorable_move)
        max_adverse = max(max_adverse, adverse_move)
        if favorable_hit:
            favorable_hits.append(position)
        if adverse_hit:
            adverse_hits.append(position)

    if favorable_hits and adverse_hits:
        label = BOTH_HIT
        if min(favorable_hits) < min(adverse_hits):
            first_hit = "FAVORABLE"
        elif min(adverse_hits) < min(favorable_hits):
            first_hit = "ADVERSE"
        else:
            first_hit = "UNKNOWN"
        notes = "Both favorable and adverse thresholds were reached."
    elif favorable_hits:
        label = FAVORABLE_MOVE
        first_hit = "FAVORABLE"
        notes = "Favorable threshold was reached."
    elif adverse_hits:
        label = ADVERSE_MOVE
        first_hit = "ADVERSE"
        notes = "Adverse threshold was reached."
    else:
        first_hit = "NONE"

    return {
        "outcome_label": label,
        "entry_reference": entry,
        "atr_reference": atr,
        "favorable_target": favorable_target,
        "adverse_target": adverse_target,
        "lookahead_candles": lookahead_candles,
        "future_candles_checked": len(df),
        "max_favorable_move": max_favorable,
        "max_adverse_move": max_adverse,
        "first_hit": first_hit,
        "notes": notes,
    }


def classify_signal_learning_result(signal: dict[str, Any], outcome: dict[str, Any]) -> dict[str, str]:
    status = signal.get("status")
    outcome_label = outcome.get("outcome_label")

    if status == REJECTED and outcome_label == FAVORABLE_MOVE:
        return {
            "learning_label": MISSED_GOOD_TRADE,
            "mistake_category": FILTER_TOO_STRICT,
            "lesson": "Rejected signal later made a favorable move; filter may be too strict.",
        }
    if status == REJECTED and outcome_label == ADVERSE_MOVE:
        return {
            "learning_label": CORRECT_REJECTION,
            "mistake_category": FILTER_PROTECTED_ACCOUNT,
            "lesson": "Rejected signal moved adversely; filter likely protected the account.",
        }
    if status == WATCHLIST and outcome_label == FAVORABLE_MOVE:
        return {
            "learning_label": MISSED_GOOD_TRADE,
            "mistake_category": FILTER_TOO_STRICT,
            "lesson": "Watchlist signal later made a favorable move; setup may deserve review.",
        }
    if status == WATCHLIST and outcome_label == ADVERSE_MOVE:
        return {
            "learning_label": CORRECT_WATCHLIST,
            "mistake_category": FILTER_PROTECTED_ACCOUNT,
            "lesson": "Watchlist signal moved adversely; caution was useful.",
        }
    if status == ELIGIBLE and outcome_label == ADVERSE_MOVE:
        return {
            "learning_label": BAD_ELIGIBLE_SIGNAL,
            "mistake_category": BAD_MARKET_CONDITION,
            "lesson": "Eligible signal moved adversely; market condition filters need review.",
        }

    return {
        "learning_label": UNCLEAR,
        "mistake_category": UNKNOWN,
        "lesson": "Outcome is not clear enough to draw a lesson yet.",
    }
