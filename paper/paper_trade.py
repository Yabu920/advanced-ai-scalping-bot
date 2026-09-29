"""Paper trade construction helpers."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

OPEN = "OPEN"
CLOSED_TP = "CLOSED_TP"
CLOSED_SL = "CLOSED_SL"
CLOSED_MANUAL = "CLOSED_MANUAL"
EXPIRED = "EXPIRED"
INVALID = "INVALID"

ELIGIBLE_SIGNAL = "ELIGIBLE_SIGNAL"
WATCHLIST_SIGNAL = "WATCHLIST_SIGNAL"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def _nested(source: dict[str, Any], *keys: str) -> Any:
    current: Any = source
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _safe_float(value: Any) -> float | None:
    try:
        parsed = float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
    return parsed if parsed is not None and math.isfinite(parsed) and parsed >= 0 else None


def _extract_signal_candle_time(plan: dict[str, Any]) -> str | None:
    candidates = [
        plan.get("opened_candle_time"),
        plan.get("signal_candle_time"),
        plan.get("latest_time"),
        plan.get("latest_candle_time"),
        _nested(plan, "details", "latest_time"),
        _nested(plan, "details", "latest_candle_time"),
        _nested(plan, "details", "latest_candle", "time"),
        _nested(plan, "signal", "latest_time"),
    ]
    for candidate in candidates:
        value = _to_iso(candidate)
        if value:
            return value
    return None


def _base_trade(plan: dict | None, validation: dict | None, modeled_costs: dict | None = None) -> dict[str, Any]:
    plan = plan or {}
    validation = validation or {}
    modeled_costs = modeled_costs or {}
    created_time = _utc_now()
    signal_candle_time = _extract_signal_candle_time(plan) or created_time
    spread_cost_check = _nested(validation, "checks", "costs", "spread_cost") or {}
    spread_cost_known = spread_cost_check.get("known") is True
    spread_cost_amount = _safe_float(spread_cost_check.get("spread_cost")) if spread_cost_known else None
    return {
        "paper_trade_id": f"paper-{uuid4()}",
        "created_time_utc": created_time,
        "opened_candle_time": signal_candle_time,
        "signal_candle_time": signal_candle_time,
        "last_evaluated_candle_time": signal_candle_time,
        "symbol": plan.get("symbol"),
        "timeframe": plan.get("timeframe"),
        "direction": plan.get("direction"),
        "source": None,
        "status": OPEN,
        "entry_price": plan.get("entry_reference"),
        "stop_loss": plan.get("stop_loss"),
        "take_profit": plan.get("take_profit"),
        "lot_size": plan.get("lot_size"),
        "risk_amount": plan.get("risk_amount"),
        "risk_percent": plan.get("risk_percent"),
        "rr_ratio": plan.get("rr_ratio"),
        "spread_points_at_entry": _safe_float(spread_cost_check.get("spread_points")),
        "spread_cost_amount": spread_cost_amount,
        "spread_cost_known": spread_cost_known and spread_cost_amount is not None,
        "commission_amount": modeled_costs.get("commission_amount"),
        "slippage_points_per_side": modeled_costs.get("slippage_points_per_side"),
        "slippage_cost_amount": modeled_costs.get("slippage_cost_amount"),
        "signal_score": plan.get("signal_score"),
        "signal_status": plan.get("signal_status"),
        "paper_experiment_name": plan.get("paper_experiment_name") or "baseline",
        "paper_filters_enabled": bool(plan.get("paper_filters_enabled", False)),
        "paper_filter_summary": plan.get("paper_filter_summary") or "filters disabled",
        "validation_summary": {
            "plan_valid": validation.get("plan_valid"),
            "broker_constraints_valid": validation.get("broker_constraints_valid"),
            "costs_valid": validation.get("costs_valid"),
            "execution_ready_later": validation.get("execution_ready_later"),
        },
        "open_reason": "",
        "close_time_utc": None,
        "close_price": None,
        "gross_pnl_amount": None,
        "gross_pnl_r": None,
        "total_cost_amount": None,
        "pnl_amount": None,
        "pnl_r": None,
        "pnl_basis": None,
        "cost_model_complete": False,
        "close_reason": None,
        "issues": [],
    }


def build_paper_trade_from_plan(plan: dict, validation: dict | None = None, modeled_costs: dict | None = None) -> dict:
    trade = _base_trade(plan, validation, modeled_costs)
    issues = trade["issues"]
    if not plan or not plan.get("valid"):
        issues.append("Plan is missing or invalid.")
    if plan.get("direction") not in {"BUY", "SELL"}:
        issues.append("Direction is not BUY or SELL.")
    if plan.get("entry_reference") is None or plan.get("stop_loss") is None or plan.get("take_profit") is None:
        issues.append("Entry, stop loss, or take profit is missing.")

    status = plan.get("signal_status")
    if status == "WATCHLIST":
        trade["source"] = WATCHLIST_SIGNAL
        trade["open_reason"] = "WATCHLIST signal opened for paper preview learning."
    elif status == "ELIGIBLE":
        trade["source"] = ELIGIBLE_SIGNAL
        trade["open_reason"] = "ELIGIBLE signal opened in paper simulation."
    else:
        issues.append("Signal status is not ELIGIBLE or WATCHLIST.")

    if issues:
        trade["status"] = INVALID
        trade["open_reason"] = "Paper trade could not be created."
    return trade
