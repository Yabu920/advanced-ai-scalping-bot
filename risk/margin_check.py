"""Defensive margin estimation for planning-only validation."""

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


def estimate_margin_requirement(plan: dict, symbol_info: dict | None, account_info: dict | None) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    constraints = extract_broker_constraints(symbol_info)
    account_info = account_info or {}
    lot = _safe_float(plan.get("lot_size"))
    free_margin = _safe_float(account_info.get("margin_free"))

    margin_initial = constraints["margin_initial"]
    if margin_initial is None or margin_initial <= 0:
        if constraints["trade_contract_size"]:
            warnings.append("Margin estimate unavailable without broker margin calculation.")
        else:
            warnings.append("Margin information is unavailable.")
        return {
            "known": False,
            "valid": True,
            "estimated_margin": None,
            "free_margin": free_margin,
            "issues": issues,
            "warnings": warnings,
        }

    if lot is None or lot <= 0:
        issues.append("Lot size is missing or invalid for margin estimate.")
        return {
            "known": True,
            "valid": False,
            "estimated_margin": None,
            "free_margin": free_margin,
            "issues": issues,
            "warnings": warnings,
        }

    estimated_margin = lot * margin_initial
    if free_margin is not None and free_margin < estimated_margin:
        issues.append("Free margin is below estimated margin requirement.")

    return {
        "known": True,
        "valid": not issues,
        "estimated_margin": estimated_margin,
        "free_margin": free_margin,
        "issues": issues,
        "warnings": warnings,
    }
