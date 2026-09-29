"""Paper-only candidate filters for controlled experiments."""

from __future__ import annotations

from typing import Any


def paper_filter_summary(settings: Any) -> str:
    """Return one auditable line describing the active paper-only admission rules."""
    def joined(name: str, fallback: str = "any") -> str:
        values = getattr(settings, name, []) or []
        return ",".join(str(value) for value in values) or fallback

    return " | ".join(
        [
            f"experiment={getattr(settings, 'paper_experiment_name', 'baseline') or 'baseline'}",
            f"enabled={str(bool(getattr(settings, 'paper_filters_enabled', False))).lower()}",
            f"symbols={joined('paper_allowed_symbols')}",
            f"timeframes={joined('paper_allowed_timeframes')}",
            f"directions={joined('paper_allowed_directions')}",
            f"min_score={float(getattr(settings, 'paper_min_signal_score', 0.0) or 0.0):g}",
            f"statuses={joined('paper_allowed_signal_statuses')}",
            f"costs_valid_required={str(bool(getattr(settings, 'paper_require_costs_valid', True))).lower()}",
            "broker_constraints_valid_required="
            f"{str(bool(getattr(settings, 'paper_require_broker_constraints_valid', True))).lower()}",
        ]
    )


def _value(source: dict[str, Any], key: str) -> Any:
    if key in source:
        return source.get(key)
    for section in ("plan", "validation"):
        nested = source.get(section)
        if isinstance(nested, dict) and key in nested:
            return nested.get(key)
    return None


def paper_trade_allowed_by_filters(plan_or_validation: dict[str, Any], settings: Any) -> tuple[bool, list[str]]:
    if not getattr(settings, "paper_filters_enabled", False):
        return True, []

    reasons: list[str] = []
    symbol = str(_value(plan_or_validation, "symbol") or "").upper()
    timeframe = str(_value(plan_or_validation, "timeframe") or "").upper()
    direction = str(_value(plan_or_validation, "direction") or "").upper()
    signal_status = str(_value(plan_or_validation, "signal_status") or "").upper()
    try:
        signal_score = float(_value(plan_or_validation, "signal_score") or 0.0)
    except (TypeError, ValueError):
        signal_score = 0.0

    allowed_symbols = {str(value).upper() for value in getattr(settings, "paper_allowed_symbols", [])}
    allowed_timeframes = {str(value).upper() for value in getattr(settings, "paper_allowed_timeframes", [])}
    allowed_directions = {str(value).upper() for value in getattr(settings, "paper_allowed_directions", [])}
    allowed_statuses = {str(value).upper() for value in getattr(settings, "paper_allowed_signal_statuses", [])}

    if allowed_symbols and symbol not in allowed_symbols:
        reasons.append(f"symbol {symbol or 'UNKNOWN'} not allowed")
    if allowed_timeframes and timeframe not in allowed_timeframes:
        reasons.append(f"timeframe {timeframe or 'UNKNOWN'} not allowed")
    if allowed_directions and direction not in allowed_directions:
        reasons.append(f"direction {direction or 'UNKNOWN'} not allowed")
    minimum_score = float(getattr(settings, "paper_min_signal_score", 0.0) or 0.0)
    if signal_score < minimum_score:
        reasons.append(f"signal score {signal_score:g} below paper minimum {minimum_score:g}")
    if allowed_statuses and signal_status not in allowed_statuses:
        reasons.append(f"signal status {signal_status or 'UNKNOWN'} not allowed")
    if getattr(settings, "paper_require_costs_valid", True) and _value(plan_or_validation, "costs_valid") is not True:
        reasons.append("costs invalid")
    if (
        getattr(settings, "paper_require_broker_constraints_valid", True)
        and _value(plan_or_validation, "broker_constraints_valid") is not True
    ):
        reasons.append("broker constraints invalid")

    return not reasons, reasons
