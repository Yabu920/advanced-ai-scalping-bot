"""Aggregate paper trading performance reports."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _safe_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _group_stats(closed_trades: list[dict], key: str) -> dict[str, dict[str, float]]:
    groups: dict[str, list[dict]] = {}
    for trade in closed_trades:
        groups.setdefault(str(trade.get(key)), []).append(trade)
    return {
        group: {
            "total_closed": len(items),
            "wins": len([trade for trade in items if _safe_float(trade.get("pnl_r")) > 0]),
            "losses": len([trade for trade in items if _safe_float(trade.get("pnl_r")) < 0]),
            "total_pnl": sum(_safe_float(trade.get("pnl_amount")) for trade in items),
            "total_r": sum(_safe_float(trade.get("pnl_r")) for trade in items),
        }
        for group, items in groups.items()
    }


def calculate_paper_performance(closed_trades: list[dict]) -> dict:
    r_values = [_safe_float(trade.get("pnl_r")) for trade in closed_trades]
    wins = len([value for value in r_values if value > 0])
    losses = len([value for value in r_values if value < 0])
    total_closed = len(closed_trades)
    total_pnl = sum(_safe_float(trade.get("pnl_amount")) for trade in closed_trades)
    total_r = sum(r_values)
    return {
        "total_closed": total_closed,
        "wins": wins,
        "losses": losses,
        "win_rate": wins / total_closed * 100 if total_closed else 0.0,
        "total_pnl": total_pnl,
        "total_r": total_r,
        "average_r": total_r / total_closed if total_closed else 0.0,
        "best_trade_r": max(r_values) if r_values else 0.0,
        "worst_trade_r": min(r_values) if r_values else 0.0,
        "by_symbol": _group_stats(closed_trades, "symbol"),
        "by_timeframe": _group_stats(closed_trades, "timeframe"),
    }


def append_performance_snapshot(performance: dict, csv_path: str) -> None:
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["snapshot_time_utc", "total_closed", "wins", "losses", "win_rate", "total_pnl", "total_r", "average_r", "best_trade_r", "worst_trade_r"]
    file_exists = path.exists() and path.stat().st_size > 0
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        if not file_exists:
            writer.writeheader()
        writer.writerow({"snapshot_time_utc": datetime.now(timezone.utc).isoformat(), **{field: performance.get(field) for field in fields if field != "snapshot_time_utc"}})
