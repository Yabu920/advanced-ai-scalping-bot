"""Account normalization and risk amount calculations."""

from __future__ import annotations

from typing import Any


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_account_info(account_info: dict | None) -> dict:
    account_info = account_info or {}
    return {
        "login": account_info.get("login"),
        "balance": _safe_float(account_info.get("balance")),
        "equity": _safe_float(account_info.get("equity")),
        "currency": account_info.get("currency"),
    }


def calculate_risk_amount(
    account: dict,
    risk_percent: float,
    use_fixed_risk: bool = False,
    fixed_risk_amount: float = 0.0,
) -> float:
    if use_fixed_risk and fixed_risk_amount > 0:
        return float(fixed_risk_amount)

    equity = _safe_float(account.get("equity"))
    balance = _safe_float(account.get("balance"))
    base_amount = equity if equity > 0 else balance
    risk_amount = base_amount * max(risk_percent, 0) / 100
    return max(risk_amount, 0.0)
