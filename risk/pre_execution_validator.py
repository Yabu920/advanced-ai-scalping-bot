"""Pre-execution validation for Stage 8 planning diagnostics."""

from __future__ import annotations

from typing import Any

from risk.broker_constraints import validate_stop_and_tp_distance, validate_trade_mode, validate_volume_constraints
from risk.margin_check import estimate_margin_requirement
from risk.trading_costs import validate_trading_costs


def _atr_from_plan(plan: dict) -> float | None:
    atr = plan.get("atr_reference")
    return float(atr) if atr else None


class PreExecutionValidator:
    """Validate trade plans without creating or sending orders."""

    def validate_signal_status(self, plan: dict, settings: Any) -> dict[str, Any]:
        status = plan.get("signal_status")
        issues: list[str] = []
        warnings: list[str] = []
        preview_only = False
        if status == "ELIGIBLE":
            valid = True
        elif status == "WATCHLIST":
            preview_only = True
            valid = bool(settings.allow_watchlist_plan_preview)
            issues.append("Signal is WATCHLIST; preview only.")
        elif status == "REJECTED":
            valid = False
            issues.append("Signal is REJECTED; no execution.")
        else:
            valid = False
            issues.append("Unknown signal status.")
        if settings.require_eligible_signal_for_execution and status != "ELIGIBLE":
            preview_only = status == "WATCHLIST"
        return {"valid": valid, "issues": issues, "warnings": warnings, "preview_only": preview_only}

    def validate_plan(
        self,
        plan: dict,
        symbol_info: dict | None,
        account_info: dict | None,
        spread_points: float | None,
        settings: Any,
    ) -> dict[str, Any]:
        status_check = self.validate_signal_status(plan, settings)
        distances = validate_stop_and_tp_distance(plan, symbol_info, settings)
        volume = validate_volume_constraints(plan, symbol_info)
        trade_mode = validate_trade_mode(symbol_info)
        costs = validate_trading_costs(plan, symbol_info, spread_points, _atr_from_plan(plan), settings)
        margin = estimate_margin_requirement(plan, symbol_info, account_info) if settings.check_margin_requirement else {
            "known": False, "valid": True, "estimated_margin": None, "free_margin": None, "issues": [], "warnings": ["Margin check disabled."]
        }

        issues = (
            list(plan.get("issues", []))
            + status_check["issues"]
            + distances["issues"]
            + volume["issues"]
            + trade_mode["issues"]
            + costs["issues"]
            + margin["issues"]
        )
        warnings = status_check["warnings"] + distances["warnings"] + trade_mode["warnings"] + costs["warnings"] + margin["warnings"]

        plan_valid = bool(plan.get("valid"))
        broker_valid = distances["valid"] and volume["valid"] and trade_mode["valid"]
        costs_valid = costs["valid"]
        margin_valid = margin["valid"]
        execution_ready = (
            plan.get("signal_status") == "ELIGIBLE"
            and plan_valid
            and broker_valid
            and costs_valid
            and margin_valid
            and not issues
        )

        return {
            "symbol": plan.get("symbol"),
            "timeframe": plan.get("timeframe"),
            "direction": plan.get("direction"),
            "signal_status": plan.get("signal_status"),
            "plan_valid": plan_valid,
            "broker_constraints_valid": broker_valid,
            "costs_valid": costs_valid,
            "margin_valid": margin_valid,
            "preview_only": status_check["preview_only"],
            "execution_ready_later": execution_ready,
            "issues": issues,
            "warnings": warnings,
            "checks": {
                "signal_status": status_check,
                "distances": distances,
                "volume": volume,
                "trade_mode": trade_mode,
                "costs": costs,
                "margin": margin,
            },
        }

    def validate_plans(
        self,
        plans: dict,
        symbol_info_map: dict[str, dict],
        account_info: dict | None,
        spread_map: dict[str, float | None],
        settings: Any,
    ) -> dict[str, Any]:
        return {
            symbol: {
                timeframe: self.validate_plan(plan, symbol_info_map.get(symbol), account_info, spread_map.get(symbol), settings)
                for timeframe, plan in symbol_plans.items()
            }
            for symbol, symbol_plans in plans.items()
        }
