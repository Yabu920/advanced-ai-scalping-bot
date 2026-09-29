"""Broker-aware lot size estimation."""

from __future__ import annotations

import math
from typing import Any


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 5) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def get_symbol_trade_specs(symbol_info: dict | None) -> dict:
    symbol_info = symbol_info or {}
    name = str(symbol_info.get("name", "")).upper()
    default_point = 0.01 if "XAUUSD" in name else 0.00001
    return {
        "point": _safe_float(symbol_info.get("point"), default_point) or default_point,
        "digits": _safe_int(symbol_info.get("digits"), 2 if "XAUUSD" in name else 5),
        "trade_tick_size": _safe_float(symbol_info.get("trade_tick_size")),
        "trade_tick_value": _safe_float(symbol_info.get("trade_tick_value")),
        "volume_min": _safe_float(symbol_info.get("volume_min"), 0.01) or 0.01,
        "volume_max": _safe_float(symbol_info.get("volume_max"), 100.0) or 100.0,
        "volume_step": _safe_float(symbol_info.get("volume_step"), 0.01) or 0.01,
    }


def round_volume_to_step(volume: float, volume_step: float, volume_min: float, volume_max: float) -> float:
    if volume <= 0 or volume_step <= 0 or volume_min <= 0 or volume_max <= 0:
        return 0.0
    rounded = math.floor(volume / volume_step) * volume_step
    if rounded < volume_min:
        return 0.0
    rounded = min(rounded, volume_max)
    decimals = max(0, len(str(volume_step).split(".")[-1].rstrip("0")))
    return round(rounded, decimals)


def estimate_lot_size(
    symbol: str,
    entry_price: float,
    stop_loss: float,
    risk_amount: float,
    symbol_info: dict | None,
) -> dict:
    info = dict(symbol_info or {})
    info.setdefault("name", symbol)
    specs = get_symbol_trade_specs(info)
    issues: list[str] = []

    tick_size = specs["trade_tick_size"]
    tick_value = specs["trade_tick_value"]
    if tick_size is None or tick_size <= 0 or tick_value is None or tick_value <= 0:
        issues.append("Missing tick value/tick size; cannot safely estimate lot size.")
        return {
            "valid": False,
            "lot_size": 0.0,
            "raw_lot_size": 0.0,
            "risk_per_lot": 0.0,
            "risk_amount": risk_amount,
            "issues": issues,
            "symbol_specs": specs,
        }

    stop_distance = abs(entry_price - stop_loss)
    if stop_distance <= 0 or risk_amount <= 0:
        issues.append("Invalid stop distance or risk amount.")
        return {
            "valid": False,
            "lot_size": 0.0,
            "raw_lot_size": 0.0,
            "risk_per_lot": 0.0,
            "risk_amount": risk_amount,
            "issues": issues,
            "symbol_specs": specs,
        }

    risk_per_lot = stop_distance / tick_size * tick_value
    raw_lot = risk_amount / risk_per_lot if risk_per_lot > 0 else 0.0
    lot = round_volume_to_step(raw_lot, specs["volume_step"], specs["volume_min"], specs["volume_max"])
    if lot <= 0:
        issues.append("Calculated lot size is below broker minimum or invalid.")

    return {
        "valid": not issues,
        "lot_size": lot,
        "raw_lot_size": raw_lot,
        "risk_per_lot": risk_per_lot,
        "risk_amount": risk_amount,
        "issues": issues,
        "symbol_specs": specs,
    }
