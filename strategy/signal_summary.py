"""Readable signal candidate summaries."""

from __future__ import annotations

from typing import Any


def build_signal_summary(signals: dict[str, Any]) -> str:
    lines = [
        "Signal Candidate Summary",
        "========================",
        "",
    ]

    if not signals:
        lines.append("No signal candidates available.")
        return "\n".join(lines)

    for symbol, symbol_result in signals.items():
        bias = symbol_result.get("bias", {})
        lines.append(str(symbol))
        lines.append(f"Bias: {bias.get('bias', 'unknown')} | Confidence: {bias.get('confidence', 0)}")
        for timeframe, signal in symbol_result.get("signals", {}).items():
            reasons = signal.get("rejection_reasons", [])
            reason_text = ", ".join(reasons) if reasons else "none"
            lines.append(
                f"- {timeframe}: {signal.get('direction', 'NO_TRADE')} | "
                f"{signal.get('status', 'REJECTED')} | "
                f"Score: {signal.get('score', 0)}/{signal.get('max_score', 100)} | "
                f"Reasons: {reason_text}"
            )
        lines.append("")

    return "\n".join(lines).rstrip()
