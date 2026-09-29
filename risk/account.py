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
    max_risk_percent: float | None = None,
) -> float:
    equity = _safe_float(account.get("equity"))
    balance = _safe_float(account.get("balance"))
    base_amount = equity if equity > 0 else balance

    if use_fixed_risk and fixed_risk_amount > 0:
        risk_amount = float(fixed_risk_amount)
    else:
        risk_amount = base_amount * max(risk_percent, 0) / 100

    if max_risk_percent is not None:
        if base_amount <= 0:
            return 0.0
        maximum_risk_amount = base_amount * max(max_risk_percent, 0) / 100
        risk_amount = min(risk_amount, maximum_risk_amount)
    return max(risk_amount, 0.0)


def calculate_effective_risk_percent(account: dict, risk_amount: float) -> float:
    equity = _safe_float(account.get("equity"))
    balance = _safe_float(account.get("balance"))
    base_amount = equity if equity > 0 else balance
    if base_amount <= 0:
        return 0.0
    return max(_safe_float(risk_amount), 0.0) / base_amount * 100
