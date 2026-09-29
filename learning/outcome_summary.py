"""Readable summaries for Stage 6 outcome tracking."""

from __future__ import annotations

from collections import Counter


def build_outcome_summary(results: list[dict]) -> str:
    lines = [
        "Signal Outcome Tracking Summary",
        "===============================",
        "",
        f"Checked events: {len(results)}",
        "",
    ]

    if not results:
        lines.append("No signal events were evaluated.")
        return "\n".join(lines)

    outcome_counts = Counter(result.get("outcome_label", "UNKNOWN") for result in results)
    learning_counts = Counter(result.get("learning_label", "UNCLEAR") for result in results)

    lines.append("By Outcome:")
    for label, count in outcome_counts.items():
        lines.append(f"- {label}: {count}")

    lines.append("")
    lines.append("Learning Labels:")
    for label, count in learning_counts.items():
        lines.append(f"- {label}: {count}")

    lines.append("")
    lines.append("Recent Lessons:")
    for result in results[-5:]:
        lines.append(
            "- "
            f"{result.get('symbol')} {result.get('timeframe')} "
            f"{result.get('direction')} {result.get('status')} became "
            f"{result.get('outcome_label')}: possible {result.get('mistake_category')}."
        )

    return "\n".join(lines)
