"""Readable paper trading status summaries."""

from __future__ import annotations

from typing import Any


def _fmt(value: Any, digits: int = 5) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _money(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "N/A"
    sign = "+" if value >= 0 else "-"
    return f"{sign}${abs(value):.2f}"


def build_paper_status_summary(report: dict, performance: dict) -> str:
    lines = [
        "Paper Trading Status Summary",
        "============================",
        "",
        f"Open trades: {report.get('open_count', 0)}",
        f"Closed trades: {performance.get('total_closed', 0)}",
        f"Wins: {performance.get('wins', 0)} | Losses: {performance.get('losses', 0)} | Win rate: {performance.get('win_rate', 0.0):.1f}%",
        f"Total PnL: {_money(performance.get('total_pnl', 0.0))} | Total R: {performance.get('total_r', 0.0):+.1f}R",
        "",
        "Open Trades:",
    ]

    open_trades = report.get("open_trades", [])
    if open_trades:
        for trade in open_trades:
            metrics = trade.get("floating_metrics", {})
            lines.extend(
                [
                    f"- {trade.get('symbol')} {trade.get('timeframe')} {trade.get('direction')} {trade.get('status')}",
                    f"  Entry: {_fmt(trade.get('entry_price'))} | Current: {_fmt(metrics.get('current_price'))} | SL: {_fmt(trade.get('stop_loss'))} | TP: {_fmt(trade.get('take_profit'))}",
                    f"  Floating: {_fmt(metrics.get('floating_r'), 2)}R | {_money(metrics.get('floating_pnl_estimate'))} | Progress to TP: {_fmt(metrics.get('progress_to_tp_percent'), 0)}%",
                ]
            )
            warning = trade.get("execution_warning", {})
            if warning.get("warning"):
                lines.append(f"  {warning.get('message')}")
    else:
        lines.append("No open paper trades.")

    lines.extend(["", "Recent Closed Trades:"])
    closed_trades = report.get("closed_trades", [])[-5:]
    if closed_trades:
        for trade in closed_trades:
            lines.append(
                f"- {trade.get('symbol')} {trade.get('timeframe')} {trade.get('direction')} {trade.get('status')} | "
                f"{_money(trade.get('pnl_amount'))} | {_fmt(trade.get('pnl_r'), 1)}R"
            )
    else:
        lines.append("No closed paper trades.")

    return "\n".join(lines)
