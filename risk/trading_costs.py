"""Trading cost and spread-efficiency validation."""

from __future__ import annotations

from typing import Any

from risk.broker_constraints import extract_broker_constraints


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def estimate_spread_cost(plan: dict, symbol_info: dict | None, spread_points: float | None) -> dict[str, Any]:
    issues: list[str] = []
    constraints = extract_broker_constraints(symbol_info)
    lot = _safe_float(plan.get("lot_size"))
    risk_amount = _safe_float(plan.get("risk_amount"))
    if spread_points is None:
        issues.append("Spread points are unavailable.")
        return {"known": False, "spread_points": None, "spread_price_distance": None, "spread_cost": None, "spread_cost_risk_percent": None, "issues": issues}

    tick_size = constraints["trade_tick_size"]
    tick_value = constraints["trade_tick_value"]
    if tick_size is None or tick_size <= 0 or tick_value is None or tick_value <= 0 or lot is None or lot <= 0:
        issues.append("Missing tick value/tick size; spread cost cannot be estimated safely.")
        return {"known": False, "spread_points": spread_points, "spread_price_distance": None, "spread_cost": None, "spread_cost_risk_percent": None, "issues": issues}

    spread_price_distance = spread_points * constraints["point"]
    spread_ticks = spread_price_distance / tick_size
    spread_cost = spread_ticks * tick_value * lot
    risk_percent = spread_cost / risk_amount * 100 if risk_amount and risk_amount > 0 else None
    return {
        "known": True,
        "spread_points": float(spread_points),
        "spread_price_distance": spread_price_distance,
        "spread_cost": spread_cost,
        "spread_cost_risk_percent": risk_percent,
        "issues": issues,
    }


def calculate_spread_ratios(
    plan: dict,
    symbol_info: dict | None,
    spread_points: float | None,
    atr_value: float | None,
) -> dict[str, Any]:
    issues: list[str] = []
    if spread_points is None:
        issues.append("Spread points are unavailable.")
        return {"spread_to_atr_ratio": None, "spread_to_sl_ratio": None, "spread_to_tp_ratio": None, "issues": issues}

    constraints = extract_broker_constraints(symbol_info)
    spread_distance = spread_points * constraints["point"]
    entry = _safe_float(plan.get("entry_reference"))
    stop_loss = _safe_float(plan.get("stop_loss"))
    take_profit = _safe_float(plan.get("take_profit"))
    sl_distance = abs(entry - stop_loss) if entry is not None and stop_loss is not None else None
    tp_distance = abs(take_profit - entry) if entry is not None and take_profit is not None else None

    return {
        "spread_to_atr_ratio": spread_distance / atr_value if atr_value and atr_value > 0 else None,
        "spread_to_sl_ratio": spread_distance / sl_distance if sl_distance and sl_distance > 0 else None,
        "spread_to_tp_ratio": spread_distance / tp_distance if tp_distance and tp_distance > 0 else None,
        "issues": issues,
    }


def calculate_net_rr_after_spread(plan: dict, symbol_info: dict | None, spread_points: float | None) -> dict[str, Any]:
    issues: list[str] = []
    if spread_points is None:
        issues.append("Spread points are unavailable.")
        return {"known": False, "gross_rr": None, "net_rr_after_spread": None, "issues": issues}

    constraints = extract_broker_constraints(symbol_info)
    entry = _safe_float(plan.get("entry_reference"))
    stop_loss = _safe_float(plan.get("stop_loss"))
    take_profit = _safe_float(plan.get("take_profit"))
    if entry is None or stop_loss is None or take_profit is None:
        issues.append("Missing entry, stop loss, or take profit.")
        return {"known": False, "gross_rr": None, "net_rr_after_spread": None, "issues": issues}

    gross_risk = abs(entry - stop_loss)
    gross_reward = abs(take_profit - entry)
    if gross_risk <= 0:
        issues.append("Gross risk distance is invalid.")
        return {"known": False, "gross_rr": None, "net_rr_after_spread": None, "issues": issues}

    spread_distance = spread_points * constraints["point"]
    net_reward = gross_reward - spread_distance
    return {
        "known": True,
        "gross_rr": gross_reward / gross_risk,
        "net_rr_after_spread": net_reward / gross_risk,
        "issues": issues,
    }


def validate_trading_costs(
    plan: dict,
    symbol_info: dict | None,
    spread_points: float | None,
    atr_value: float | None,
    settings: Any,
) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    spread_cost = estimate_spread_cost(plan, symbol_info, spread_points)
    ratios = calculate_spread_ratios(plan, symbol_info, spread_points, atr_value)
    net_rr = calculate_net_rr_after_spread(plan, symbol_info, spread_points)

    for key, limit, label in [
        ("spread_to_atr_ratio", settings.max_spread_to_atr_ratio, "Spread/ATR ratio"),
        ("spread_to_sl_ratio", settings.max_spread_to_sl_ratio, "Spread/SL ratio"),
        ("spread_to_tp_ratio", settings.max_spread_to_tp_ratio, "Spread/TP ratio"),
    ]:
        value = ratios.get(key)
        if value is not None and value > limit:
            issues.append(f"{label} is too high.")

    cost_risk_percent = spread_cost.get("spread_cost_risk_percent")
    if spread_cost["known"] and cost_risk_percent is not None and cost_risk_percent > settings.max_spread_cost_risk_percent:
        issues.append("Spread cost is too high compared to risk amount.")
    elif not spread_cost["known"]:
        warnings.extend(spread_cost["issues"])

    net_rr_value = net_rr.get("net_rr_after_spread")
    if net_rr["known"] and net_rr_value is not None and net_rr_value < settings.min_net_rr_after_spread:
        issues.append("Net RR after spread is below minimum.")
    elif not net_rr["known"]:
        warnings.extend(net_rr["issues"])

    warnings.extend(ratios["issues"])
    return {
        "valid": not issues,
        "issues": issues,
        "warnings": warnings,
        "spread_cost": spread_cost,
        "spread_ratios": ratios,
        "net_rr": net_rr,
    }
