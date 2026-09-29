"""Stop loss and take profit helpers."""

from __future__ import annotations


def calculate_atr_stop_distance(
    atr_value: float,
    atr_multiplier: float,
    min_multiplier: float,
    max_multiplier: float,
) -> float:
    if atr_value is None or atr_value <= 0:
        return 0.0
    multiplier = min(max(atr_multiplier, min_multiplier), max_multiplier)
    return float(atr_value) * multiplier


def build_sl_tp_prices(
    direction: str,
    entry_price: float,
    stop_distance: float,
    rr_ratio: float,
) -> dict:
    if direction == "BUY":
        stop_loss = entry_price - stop_distance
        take_profit = entry_price + stop_distance * rr_ratio
    elif direction == "SELL":
        stop_loss = entry_price + stop_distance
        take_profit = entry_price - stop_distance * rr_ratio
    else:
        stop_loss = None
        take_profit = None

    return {
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "stop_distance": stop_distance,
        "tp_distance": stop_distance * rr_ratio if stop_distance > 0 else 0.0,
        "rr_ratio": rr_ratio,
    }


def validate_sl_tp(direction: str, entry_price: float, stop_loss: float, take_profit: float) -> dict:
    issues: list[str] = []
    if entry_price is None or stop_loss is None or take_profit is None:
        issues.append("Missing entry, stop loss, or take profit.")
        return {"valid": False, "issues": issues}

    if direction == "BUY":
        if not stop_loss < entry_price < take_profit:
            issues.append("BUY requires stop_loss < entry_price < take_profit.")
    elif direction == "SELL":
        if not take_profit < entry_price < stop_loss:
            issues.append("SELL requires take_profit < entry_price < stop_loss.")
    else:
        issues.append("Direction must be BUY or SELL.")

    if abs(entry_price - stop_loss) <= 0:
        issues.append("Stop distance must be greater than zero.")
    if abs(take_profit - entry_price) <= 0:
        issues.append("Take-profit distance must be greater than zero.")

    return {"valid": not issues, "issues": issues}
