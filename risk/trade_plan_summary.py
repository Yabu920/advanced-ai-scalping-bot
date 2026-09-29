"""Readable summaries for Stage 7 trade plans."""

from __future__ import annotations

from typing import Any


def _fmt(value: Any, digits: int = 5) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def build_trade_plan_summary(plans: dict[str, Any]) -> str:
    lines = [
        "Trade Plan Summary",
        "==================",
        "",
    ]
    valid_count = 0

    if not plans:
        lines.append("No executable trade plans found. This is expected if no signals are ELIGIBLE.")
        return "\n".join(lines)

    for symbol, symbol_plans in plans.items():
        lines.append(str(symbol))
        for timeframe, plan in symbol_plans.items():
            status = plan.get("signal_status")
            direction = plan.get("direction")
            if status == "REJECTED":
                lines.append(f"- {timeframe}: {direction} | REJECTED signal | no plan")
                continue

            mode = "executable later" if plan.get("executable_later") else "preview only"
            validity = "valid" if plan.get("valid") else "invalid"
            if plan.get("valid"):
                valid_count += 1
            lines.append(
                f"- {timeframe}: {direction} | {status} | {mode} | {validity} | "
                f"entry {_fmt(plan.get('entry_reference'))} | "
                f"SL {_fmt(plan.get('stop_loss'))} | "
                f"TP {_fmt(plan.get('take_profit'))} | "
                f"lot {_fmt(plan.get('lot_size'), 2)} | "
                f"risk ${_fmt(plan.get('risk_amount'), 2)}"
            )
        lines.append("")

    if valid_count == 0:
        lines.append("No executable trade plans found. This is expected if no signals are ELIGIBLE.")

    return "\n".join(lines).rstrip()
