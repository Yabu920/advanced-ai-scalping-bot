"""Readable Stage 10 paper performance analysis summaries."""

from __future__ import annotations

from typing import Any


def _fmt(value: Any, digits: int = 2) -> str:
    if value == float("inf"):
        return "inf"
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}"
    return str(value)


def _group_lines(group: dict[str, dict[str, Any]]) -> list[str]:
    if not group:
        return ["- none"]
    lines = []
    for key, stats in sorted(group.items()):
        lines.append(f"- {key}: {stats.get('trades', 0)} trades | {stats.get('total_r', 0.0):+.1f}R | ${stats.get('total_pnl', 0.0):+.2f}")
    return lines


def build_paper_analysis_markdown(analysis: dict[str, Any]) -> str:
    lines = [
        "# Clean Paper Performance Analysis",
        "",
        f"Closed trades: {analysis.get('total_closed', 0)}",
        f"Wins: {analysis.get('wins', 0)} | Losses: {analysis.get('losses', 0)} | Win rate: {analysis.get('win_rate', 0.0):.1f}%",
        f"Total R: {analysis.get('total_r', 0.0):+.1f}R",
        f"Total PnL: ${analysis.get('total_pnl', 0.0):+.2f}",
        f"Average R/trade: {analysis.get('average_r', 0.0):+.2f}R",
        f"Profit factor: {_fmt(analysis.get('profit_factor', 0.0))}",
        f"Expectancy: {analysis.get('expectancy', 0.0):+.2f}R",
        f"Max drawdown: {analysis.get('max_drawdown_r', 0.0):+.1f}R",
        f"Max consecutive losses: {analysis.get('max_consecutive_losses', 0)}",
        f"Max consecutive wins: {analysis.get('max_consecutive_wins', 0)}",
        "",
        "## By Experiment",
        "",
        *_group_lines(analysis.get("by_experiment", {})),
        "",
        "## By Symbol",
        "",
        *_group_lines(analysis.get("by_symbol", {})),
        "",
        "## By Timeframe",
        "",
        *_group_lines(analysis.get("by_timeframe", {})),
        "",
        "## By Direction",
        "",
        *_group_lines(analysis.get("by_direction", {})),
        "",
        "## By Signal Status",
        "",
        *_group_lines(analysis.get("by_signal_status", {})),
        "",
        "## Recommendations",
        "",
    ]

    if analysis.get("total_closed", 0) < 50:
        lines.append("- Continue paper testing until at least 50 clean closed trades are analyzed.")
    else:
        lines.append("- Review the 50-trade sample before changing strategy thresholds.")
    if analysis.get("m1_is_weak"):
        lines.append("- M1 appears weak in the current sample; consider a separate M5-only paper test later.")
    if analysis.get("best_timeframe"):
        lines.append(f"- Best timeframe so far: {analysis.get('best_timeframe')}.")
    if analysis.get("buy_performance", {}).get("total_r", 0.0) < analysis.get("sell_performance", {}).get("total_r", 0.0):
        lines.append("- SELL performance is stronger than BUY in the current sample.")
    if analysis.get("watchlist_trades_profitable"):
        lines.append("- WATCHLIST paper trades are profitable in the current sample; keep tracking them.")
    if not analysis.get("eligible_trades_exist"):
        lines.append("- No ELIGIBLE paper trades exist yet; do not move to demo execution.")

    lines.append("- This remains paper-only evidence, not permission for real/demo execution.")
    return "\n".join(lines)
