"""Readable summaries for market data collection runs."""

from __future__ import annotations

from typing import Any


def _format_time(value: Any) -> str:
    if value is None:
        return "N/A"
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def build_data_collection_summary(data: dict, validation: dict) -> str:
    lines = [
        "Market Data Collection Summary",
        "==============================",
        "",
    ]

    if not data:
        lines.append("No market data was collected.")
        return "\n".join(lines)

    for symbol, timeframe_data in data.items():
        lines.append(str(symbol))
        if not timeframe_data:
            lines.append("- no successful timeframe data")
            lines.append("")
            continue

        for timeframe, df in timeframe_data.items():
            result = validation.get(symbol, {}).get(timeframe, {})
            status = "valid" if result.get("valid") else "invalid"
            rows = result.get("rows", len(df))
            start_time = _format_time(result.get("start_time"))
            end_time = _format_time(result.get("end_time"))

            if result.get("valid"):
                lines.append(f"- {timeframe}: {rows} rows | {status} | {start_time} to {end_time}")
            else:
                issues = ", ".join(result.get("issues", [])) or "unknown"
                lines.append(f"- {timeframe}: {rows} rows | {status} | issues: {issues}")
        lines.append("")

    return "\n".join(lines).rstrip()
