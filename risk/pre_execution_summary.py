"""Readable pre-execution validation summaries."""

from __future__ import annotations

from typing import Any


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def build_pre_execution_summary(validation: dict[str, Any]) -> str:
    lines = ["Pre-Execution Validation Summary", "================================", ""]
    ready_count = 0
    for symbol, symbol_results in validation.items():
        lines.append(str(symbol))
        for timeframe, result in symbol_results.items():
            if result.get("execution_ready_later"):
                ready_count += 1
            mode = "preview only" if result.get("preview_only") else "validation"
            costs = result.get("checks", {}).get("costs", {})
            ratios = costs.get("spread_ratios", {})
            net_rr = costs.get("net_rr", {})
            spread_cost = costs.get("spread_cost", {})
            margin = result.get("checks", {}).get("margin", {})
            lines.append(
                f"- {timeframe} {result.get('direction')} | {result.get('signal_status')} | {mode} | "
                f"execution ready later: {_yes_no(result.get('execution_ready_later'))}"
            )
            lines.append(
                f"  Plan valid: {_yes_no(result.get('plan_valid'))} | "
                f"Broker constraints: {_yes_no(result.get('broker_constraints_valid'))} | "
                f"Costs: {_yes_no(result.get('costs_valid'))} | "
                f"Margin: {'yes' if margin.get('known') and margin.get('valid') else 'unknown' if not margin.get('known') else 'no'}"
            )
            if result.get("issues"):
                lines.append(f"  Issues: {'; '.join(result['issues'])}")
            if result.get("warnings"):
                lines.append(f"  Warnings: {'; '.join(result['warnings'])}")
            lines.append(f"  Net RR after spread: {_fmt(net_rr.get('net_rr_after_spread'))}")
            lines.append(f"  Spread cost risk %: {_fmt(spread_cost.get('spread_cost_risk_percent'))}")
            lines.append(f"  Spread/SL ratio: {_fmt(ratios.get('spread_to_sl_ratio'))}")
            lines.append(f"  Spread/TP ratio: {_fmt(ratios.get('spread_to_tp_ratio'))}")
        lines.append("")

    if ready_count == 0:
        lines.append("No execution-ready-later plans found. This is expected before live execution is enabled.")
    return "\n".join(lines).rstrip()
