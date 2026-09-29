"""Trade plan builder for Stage 7 planning-only diagnostics."""

from __future__ import annotations

from typing import Any

from risk.account import calculate_risk_amount, normalize_account_info
from risk.lot_size import estimate_lot_size
from risk.sl_tp import calculate_atr_stop_distance, build_sl_tp_prices, validate_sl_tp


def _nested(source: dict[str, Any], *keys: str) -> Any:
    current: Any = source
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_time(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    text = str(value).strip()
    return text or None


class TradePlanBuilder:
    """Create mathematically valid trade plans without execution permission."""

    def __init__(self, settings: Any) -> None:
        self.settings = settings

    def build_plan(
        self,
        signal: dict[str, Any],
        account_info: dict,
        symbol_info: dict | None,
    ) -> dict[str, Any]:
        symbol = signal.get("symbol")
        timeframe = signal.get("timeframe")
        direction = signal.get("direction")
        status = signal.get("status")
        issues: list[str] = []
        notes: list[str] = ["Planning only. This stage does not execute orders."]

        executable_later = status == "ELIGIBLE"
        if status == "WATCHLIST":
            notes.append("WATCHLIST signal: preview only, not executable later.")
        elif status != "ELIGIBLE":
            issues.append("Signal is not ELIGIBLE or WATCHLIST; no trade plan.")

        if direction not in {"BUY", "SELL"}:
            issues.append("Direction is not BUY or SELL.")

        entry = _safe_float(_nested(signal, "details", "latest_candle", "close"))
        atr = _safe_float(_nested(signal, "details", "latest_candle", "atr_14"))
        if atr is None:
            atr = _safe_float(_nested(signal, "details", "timeframe_analysis", "volatility", "atr_14"))
        latest_time = _safe_time(
            _nested(signal, "details", "latest_candle", "time")
            or _nested(signal, "details", "latest_time")
            or signal.get("latest_time")
        )
        if entry is None:
            issues.append("Missing entry reference price.")
        if atr is None or atr <= 0:
            issues.append("Missing or invalid ATR reference.")

        rr_ratio = self.settings.default_rr_ratio
        if rr_ratio < self.settings.min_rr_ratio:
            issues.append("RR ratio is below minimum.")

        account = normalize_account_info(account_info)
        risk_amount = calculate_risk_amount(
            account,
            self.settings.risk_per_trade_percent,
            self.settings.use_fixed_risk_amount,
            self.settings.fixed_risk_amount,
        )

        stop_distance = 0.0
        sl_tp = {"stop_loss": None, "take_profit": None, "stop_distance": 0.0, "tp_distance": 0.0, "rr_ratio": rr_ratio}
        lot_result = {"valid": False, "lot_size": 0.0, "issues": []}
        if not issues:
            stop_distance = calculate_atr_stop_distance(
                atr,
                self.settings.atr_sl_multiplier,
                self.settings.min_stop_atr_multiplier,
                self.settings.max_stop_atr_multiplier,
            )
            if stop_distance <= 0:
                issues.append("Stop distance is invalid.")
            else:
                sl_tp = build_sl_tp_prices(direction, entry, stop_distance, rr_ratio)
                sl_tp_validation = validate_sl_tp(direction, entry, sl_tp["stop_loss"], sl_tp["take_profit"])
                issues.extend(sl_tp_validation["issues"])
                lot_result = estimate_lot_size(symbol, entry, sl_tp["stop_loss"], risk_amount, symbol_info)
                issues.extend(lot_result["issues"])

        valid = not issues and lot_result.get("valid", False)
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": direction,
            "signal_status": status,
            "signal_score": signal.get("score"),
            "latest_time": latest_time,
            "signal_candle_time": latest_time,
            "opened_candle_time": latest_time,
            "executable_later": bool(executable_later and valid),
            "valid": valid,
            "entry_reference": entry,
            "atr_reference": atr,
            "stop_loss": sl_tp.get("stop_loss"),
            "take_profit": sl_tp.get("take_profit"),
            "risk_amount": risk_amount,
            "risk_percent": self.settings.risk_per_trade_percent,
            "lot_size": lot_result.get("lot_size", 0.0),
            "rr_ratio": rr_ratio,
            "stop_distance": sl_tp.get("stop_distance", stop_distance),
            "tp_distance": sl_tp.get("tp_distance", 0.0),
            "issues": issues,
            "notes": notes,
        }

    def build_plans_from_signals(
        self,
        signals: dict[str, Any],
        account_info: dict,
        symbol_info_map: dict[str, dict],
    ) -> dict[str, Any]:
        plans: dict[str, Any] = {}
        for symbol, symbol_result in signals.items():
            plans[symbol] = {}
            for timeframe, signal in symbol_result.get("signals", {}).items():
                plans[symbol][timeframe] = self.build_plan(
                    signal,
                    account_info,
                    symbol_info_map.get(symbol),
                )
        return plans
