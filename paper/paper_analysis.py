"""Clean paper trade performance analysis from JSONL trade state."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd


def _safe_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _time_value(trade: dict, key: str) -> pd.Timestamp | None:
    value = trade.get(key)
    if value is None:
        return None
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(timestamp):
        return None
    return timestamp


def _empty_group() -> dict[str, float]:
    return {
        "trades": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0.0,
        "total_r": 0.0,
        "total_pnl": 0.0,
        "average_r": 0.0,
    }


def _group_performance(closed_trades: list[dict], key_fn) -> dict[str, dict[str, float]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for trade in closed_trades:
        key = key_fn(trade)
        if key is None or key == "":
            key = "UNKNOWN"
        groups[str(key)].append(trade)

    result: dict[str, dict[str, float]] = {}
    for key, trades in groups.items():
        r_values = [_safe_float(trade.get("pnl_r")) for trade in trades]
        wins = len([value for value in r_values if value > 0])
        losses = len([value for value in r_values if value < 0])
        total = len(trades)
        total_r = sum(r_values)
        result[key] = {
            "trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": wins / total * 100 if total else 0.0,
            "total_r": total_r,
            "total_pnl": sum(_safe_float(trade.get("pnl_amount")) for trade in trades),
            "average_r": total_r / total if total else 0.0,
        }
    return result


def _best_key(group: dict[str, dict[str, float]]) -> str | None:
    if not group:
        return None
    return max(group.items(), key=lambda item: item[1].get("total_r", 0.0))[0]


def _worst_key(group: dict[str, dict[str, float]]) -> str | None:
    if not group:
        return None
    return min(group.items(), key=lambda item: item[1].get("total_r", 0.0))[0]


def _max_streak(values: list[float], predicate) -> int:
    best = 0
    current = 0
    for value in values:
        if predicate(value):
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def _max_drawdown_r(values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity - peak)
    return max_drawdown


def analyze_closed_paper_trades(closed_trades: list[dict]) -> dict[str, Any]:
    sorted_trades = sorted(closed_trades, key=lambda trade: str(trade.get("close_time_utc") or trade.get("created_time_utc") or ""))
    r_values = [_safe_float(trade.get("pnl_r")) for trade in sorted_trades]
    pnl_values = [_safe_float(trade.get("pnl_amount")) for trade in sorted_trades]
    wins = len([value for value in r_values if value > 0])
    losses = len([value for value in r_values if value < 0])
    total_closed = len(sorted_trades)
    total_r = sum(r_values)
    gross_win_r = sum(value for value in r_values if value > 0)
    gross_loss_r = abs(sum(value for value in r_values if value < 0))
    profit_factor = gross_win_r / gross_loss_r if gross_loss_r else (float("inf") if gross_win_r > 0 else 0.0)

    by_symbol = _group_performance(sorted_trades, lambda trade: trade.get("symbol"))
    by_timeframe = _group_performance(sorted_trades, lambda trade: trade.get("timeframe"))
    by_direction = _group_performance(sorted_trades, lambda trade: trade.get("direction"))
    by_signal_score = _group_performance(sorted_trades, lambda trade: trade.get("signal_score"))
    by_signal_status = _group_performance(sorted_trades, lambda trade: trade.get("signal_status"))
    by_source = _group_performance(sorted_trades, lambda trade: trade.get("source"))
    by_experiment = _group_performance(
        sorted_trades,
        lambda trade: trade.get("paper_experiment_name") or "baseline",
    )
    by_day = _group_performance(sorted_trades, lambda trade: (_time_value(trade, "close_time_utc") or _time_value(trade, "created_time_utc")).date() if (_time_value(trade, "close_time_utc") or _time_value(trade, "created_time_utc")) is not None else None)
    by_hour = _group_performance(sorted_trades, lambda trade: (_time_value(trade, "close_time_utc") or _time_value(trade, "created_time_utc")).hour if (_time_value(trade, "close_time_utc") or _time_value(trade, "created_time_utc")) is not None else None)

    m1_stats = by_timeframe.get("M1", _empty_group())
    watchlist_stats = by_signal_status.get("WATCHLIST", _empty_group())
    eligible_stats = by_signal_status.get("ELIGIBLE", _empty_group())

    return {
        "total_closed": total_closed,
        "wins": wins,
        "losses": losses,
        "win_rate": wins / total_closed * 100 if total_closed else 0.0,
        "total_r": total_r,
        "total_pnl": sum(pnl_values),
        "average_r": total_r / total_closed if total_closed else 0.0,
        "profit_factor": profit_factor,
        "expectancy": total_r / total_closed if total_closed else 0.0,
        "max_consecutive_losses": _max_streak(r_values, lambda value: value < 0),
        "max_consecutive_wins": _max_streak(r_values, lambda value: value > 0),
        "max_drawdown_r": _max_drawdown_r(r_values),
        "by_symbol": by_symbol,
        "by_timeframe": by_timeframe,
        "by_direction": by_direction,
        "by_signal_score": by_signal_score,
        "by_signal_status": by_signal_status,
        "by_source": by_source,
        "by_experiment": by_experiment,
        "by_day": by_day,
        "by_hour": by_hour,
        "best_symbol": _best_key(by_symbol),
        "worst_symbol": _worst_key(by_symbol),
        "best_timeframe": _best_key(by_timeframe),
        "worst_timeframe": _worst_key(by_timeframe),
        "buy_performance": by_direction.get("BUY", _empty_group()),
        "sell_performance": by_direction.get("SELL", _empty_group()),
        "m1_is_weak": bool(m1_stats.get("trades", 0) > 0 and m1_stats.get("total_r", 0.0) < 0),
        "watchlist_trades_profitable": bool(watchlist_stats.get("trades", 0) > 0 and watchlist_stats.get("total_r", 0.0) > 0),
        "eligible_trades_exist": bool(eligible_stats.get("trades", 0) > 0),
    }
