"""Human-readable market analysis summaries."""

from __future__ import annotations

from typing import Any


def _yes_no(value: Any) -> str:
    return "yes" if value else "no"


def build_market_analysis_summary(analysis: dict[str, Any]) -> str:
    lines = [
        "Market Analysis Summary",
        "=======================",
        "",
    ]

    if not analysis:
        lines.append("No market analysis available.")
        return "\n".join(lines)

    for symbol, symbol_result in analysis.items():
        bias = symbol_result.get("multi_timeframe_bias", {})
        lines.append(str(symbol))
        lines.append(
            "Bias: "
            f"{bias.get('bias', 'unknown')} | "
            f"Confidence: {bias.get('confidence', 0)} | "
            f"Reason: {bias.get('reason', 'N/A')}"
        )

        for timeframe, timeframe_result in symbol_result.get("timeframes", {}).items():
            trend = timeframe_result.get("trend", {})
            volatility = timeframe_result.get("volatility", {})
            spread = timeframe_result.get("spread", {})
            regime = timeframe_result.get("regime", {})
            lines.append(
                f"- {timeframe}: "
                f"{trend.get('trend', 'unknown')}/{trend.get('strength', 'weak')} | "
                f"volatility {volatility.get('volatility', 'unknown')} | "
                f"spread {spread.get('spread_quality', 'unknown')} | "
                f"regime {regime.get('regime', 'UNKNOWN')} | "
                f"tradable: {_yes_no(regime.get('tradable'))}"
            )
        lines.append("")

    return "\n".join(lines).rstrip()
