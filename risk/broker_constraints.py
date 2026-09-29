"""Broker execution constraint validation for trade plans."""

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


def _safe_int(value: Any, default: int | None = None) -> int | None:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def extract_broker_constraints(symbol_info: dict | None) -> dict[str, Any]:
    info = symbol_info or {}
    return {
        "point": _safe_float(info.get("point"), 0.00001) or 0.00001,
        "digits": _safe_int(info.get("digits"), 5) or 5,
        "volume_min": _safe_float(info.get("volume_min"), 0.01) or 0.01,
        "volume_max": _safe_float(info.get("volume_max"), 100.0) or 100.0,
        "volume_step": _safe_float(info.get("volume_step"), 0.01) or 0.01,
        "trade_stops_level": _safe_float(info.get("trade_stops_level"), 0.0) or 0.0,
        "trade_freeze_level": _safe_float(info.get("trade_freeze_level"), 0.0) or 0.0,
        "trade_mode": _safe_int(info.get("trade_mode")),
        "spread": _safe_float(info.get("spread")),
        "trade_tick_size": _safe_float(info.get("trade_tick_size")),
        "trade_tick_value": _safe_float(info.get("trade_tick_value")),
        "trade_contract_size": _safe_float(info.get("trade_contract_size")),
        "margin_initial": _safe_float(info.get("margin_initial")),
        "margin_maintenance": _safe_float(info.get("margin_maintenance")),
    }


def price_distance_to_points(price_distance: float, point: float) -> float:
    if point <= 0:
        return 0.0
    return abs(price_distance) / point


def validate_stop_and_tp_distance(plan: dict, symbol_info: dict | None, settings: Any) -> dict[str, Any]:
    constraints = extract_broker_constraints(symbol_info)
    issues: list[str] = []
    warnings: list[str] = []
    point = constraints["point"]
    entry = _safe_float(plan.get("entry_reference"), 0.0) or 0.0
    stop_loss = _safe_float(plan.get("stop_loss"), entry) or entry
    take_profit = _safe_float(plan.get("take_profit"), entry) or entry

    stop_points = price_distance_to_points(entry - stop_loss, point)
    tp_points = price_distance_to_points(take_profit - entry, point)
    required_stop = max(constraints["trade_stops_level"], settings.min_stop_distance_points)
    required_tp = max(constraints["trade_stops_level"], settings.min_tp_distance_points)

    if stop_points <= 0:
        issues.append("Stop distance must be positive.")
    if tp_points <= 0:
        issues.append("TP distance must be positive.")
    if stop_points < required_stop:
        issues.append("Stop distance is below required stop points.")
    if tp_points < required_tp:
        issues.append("TP distance is below required TP points.")
    if constraints["trade_freeze_level"] > 0:
        warnings.append("Broker freeze level is present; execution stage must respect it.")

    return {
        "valid": not issues,
        "issues": issues,
        "warnings": warnings,
        "stop_distance_points": stop_points,
        "tp_distance_points": tp_points,
        "broker_stops_level": constraints["trade_stops_level"],
        "broker_freeze_level": constraints["trade_freeze_level"],
        "required_stop_points": required_stop,
        "required_tp_points": required_tp,
    }


def validate_volume_constraints(plan: dict, symbol_info: dict | None) -> dict[str, Any]:
    constraints = extract_broker_constraints(symbol_info)
    issues: list[str] = []
    lot = _safe_float(plan.get("lot_size"))
    if lot is None or lot <= 0:
        issues.append("Lot size is missing or invalid.")
    else:
        if lot < constraints["volume_min"]:
            issues.append("Lot size is below broker minimum.")
        if lot > constraints["volume_max"]:
            issues.append("Lot size is above broker maximum.")
        remainder = (lot - constraints["volume_min"]) / constraints["volume_step"]
        if not math.isclose(remainder, round(remainder), abs_tol=1e-6):
            issues.append("Lot size does not align with broker volume step.")

    return {
        "valid": not issues,
        "issues": issues,
        "lot_size": lot,
        "volume_min": constraints["volume_min"],
        "volume_max": constraints["volume_max"],
        "volume_step": constraints["volume_step"],
    }


def validate_trade_mode(symbol_info: dict | None) -> dict[str, Any]:
    constraints = extract_broker_constraints(symbol_info)
    trade_mode = constraints["trade_mode"]
    issues: list[str] = []
    warnings: list[str] = []
    # MT5 trade mode codes vary by binding/broker. A clear 0 is treated as disabled;
    # unknown values are warnings so Stage 8 does not reject too aggressively.
    if trade_mode is None:
        warnings.append("Trade mode is unknown.")
    elif trade_mode == 0:
        issues.append("Symbol trade mode appears disabled.")

    return {
        "valid": not issues,
        "issues": issues,
        "warnings": warnings,
        "trade_mode": trade_mode,
    }
