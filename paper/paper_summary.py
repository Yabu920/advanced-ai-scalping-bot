"""Readable paper execution summaries."""

from __future__ import annotations


def _fmt(value, digits: int = 5) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def build_paper_summary(new_trades: list[dict], updated_trades: list[dict], open_trades: list[dict]) -> str:
    closed_trades = [trade for trade in updated_trades if str(trade.get("status", "")).startswith("CLOSED")]
    lines = [
        "Paper Execution Summary",
        "=======================",
        "",
        f"New paper trades opened: {len(new_trades)}",
        f"Updated open trades: {len(updated_trades)}",
        f"Currently open paper trades: {len(open_trades)}",
        "",
    ]

    lines.append("New Trades:")
    if new_trades:
        for trade in new_trades:
            lines.append(
                f"- {trade.get('symbol')} {trade.get('timeframe')} {trade.get('direction')} {trade.get('source')} | "
                f"entry {_fmt(trade.get('entry_price'))} | SL {_fmt(trade.get('stop_loss'))} | "
                f"TP {_fmt(trade.get('take_profit'))} | risk ${_fmt(trade.get('risk_amount'), 2)}"
            )
    else:
        lines.append("No new paper trades opened.")

    lines.append("")
    lines.append("Closed Trades:")
    if closed_trades:
        for trade in closed_trades:
            pnl = trade.get("pnl_amount")
            pnl_text = f"+${pnl:.2f}" if isinstance(pnl, float) and pnl >= 0 else f"-${abs(pnl):.2f}" if isinstance(pnl, float) else "N/A"
            lines.append(
                f"- {trade.get('symbol')} {trade.get('timeframe')} {trade.get('direction')} {trade.get('status')} | "
                f"PnL {pnl_text} | {trade.get('pnl_r')}R"
            )
    else:
        lines.append("No paper trades closed.")

    lines.append("")
    lines.append("Open Trades:")
    if open_trades:
        for trade in open_trades:
            lines.append(
                f"- {trade.get('symbol')} {trade.get('timeframe')} {trade.get('direction')} OPEN | "
                f"entry {_fmt(trade.get('entry_price'))} | SL {_fmt(trade.get('stop_loss'))} | TP {_fmt(trade.get('take_profit'))}"
            )
    else:
        lines.append("No open paper trades.")

    return "\n".join(lines)
