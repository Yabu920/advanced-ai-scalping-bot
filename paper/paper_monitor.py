"""Paper trade monitoring and floating metrics."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from paper.paper_trade import CLOSED_SL, CLOSED_TP, OPEN


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def calculate_floating_metrics(trade: dict, current_price: float | None) -> dict[str, Any]:
    notes: list[str] = []
    entry = _safe_float(trade.get("entry_price"))
    stop_loss = _safe_float(trade.get("stop_loss"))
    take_profit = _safe_float(trade.get("take_profit"))
    risk_amount = _safe_float(trade.get("risk_amount")) or 0.0
    if current_price is None or entry is None or stop_loss is None or take_profit is None:
        return {
            "current_price": current_price,
            "distance_to_tp": None,
            "distance_to_sl": None,
            "floating_r": None,
            "floating_pnl_estimate": None,
            "progress_to_tp_percent": None,
            "notes": "Missing current price or trade levels.",
        }

    direction = trade.get("direction")
    risk_distance = abs(entry - stop_loss)
    reward_distance = abs(take_profit - entry)
    if risk_distance <= 0 or reward_distance <= 0:
        notes.append("Invalid risk or reward distance.")
        risk_distance = None

    if direction == "BUY":
        floating_move = current_price - entry
        distance_to_tp = take_profit - current_price
        distance_to_sl = current_price - stop_loss
    elif direction == "SELL":
        floating_move = entry - current_price
        distance_to_tp = current_price - take_profit
        distance_to_sl = stop_loss - current_price
    else:
        notes.append("Unknown direction.")
        floating_move = 0.0
        distance_to_tp = None
        distance_to_sl = None

    floating_r = floating_move / risk_distance if risk_distance else None
    progress = floating_move / reward_distance * 100 if reward_distance > 0 else None
    return {
        "current_price": current_price,
        "distance_to_tp": distance_to_tp,
        "distance_to_sl": distance_to_sl,
        "floating_r": floating_r,
        "floating_pnl_estimate": floating_r * risk_amount if floating_r is not None else None,
        "progress_to_tp_percent": progress,
        "notes": " ".join(notes),
    }


def _latest_closed_candle(df: pd.DataFrame) -> dict | None:
    if df.empty:
        return None
    if "is_closed_candle" in df.columns:
        closed = df[df["is_closed_candle"] == True]
        if closed.empty:
            return None
        return closed.iloc[-1].to_dict()
    if len(df) < 2:
        return None
    return df.iloc[-2].to_dict()


def detect_open_trade_price_breach(trade: dict, latest_closed_candle: dict | None) -> dict[str, Any]:
    warning = {
        "warning": False,
        "message": "",
        "breach_type": None,
        "candle_time": latest_closed_candle.get("time") if latest_closed_candle else None,
    }
    if trade.get("status") != OPEN or latest_closed_candle is None:
        return warning

    high = _safe_float(latest_closed_candle.get("high"))
    low = _safe_float(latest_closed_candle.get("low"))
    stop_loss = _safe_float(trade.get("stop_loss"))
    take_profit = _safe_float(trade.get("take_profit"))
    direction = trade.get("direction")
    if high is None or low is None or stop_loss is None or take_profit is None:
        return warning

    if direction == "BUY":
        sl_hit = low <= stop_loss
        tp_hit = high >= take_profit
    elif direction == "SELL":
        sl_hit = high >= stop_loss
        tp_hit = low <= take_profit
    else:
        return warning

    if sl_hit or tp_hit:
        breach_type = "SL" if sl_hit else "TP"
        warning.update(
            {
                "warning": True,
                "message": "WARNING: Open trade appears beyond SL/TP but has not been closed by execution.",
                "breach_type": breach_type,
            }
        )
    return warning


def enrich_open_trades_with_market_data(open_trades: list[dict], market_data: dict[str, dict[str, pd.DataFrame]]) -> list[dict]:
    enriched: list[dict] = []
    for trade in open_trades:
        item = dict(trade)
        df = market_data.get(trade.get("symbol"), {}).get(trade.get("timeframe"))
        candle = _latest_closed_candle(df) if df is not None else None
        current_price = _safe_float(candle.get("close")) if candle else None
        item["floating_metrics"] = calculate_floating_metrics(trade, current_price)
        item["latest_candle_time"] = candle.get("time") if candle else None
        item["execution_warning"] = detect_open_trade_price_breach(trade, candle)
        enriched.append(item)
    return enriched


def build_paper_status_report(open_trades: list[dict], closed_trades: list[dict]) -> dict[str, Any]:
    total_pnl = sum(_safe_float(trade.get("pnl_amount")) or 0.0 for trade in closed_trades)
    total_r = sum(_safe_float(trade.get("pnl_r")) or 0.0 for trade in closed_trades)
    return {
        "report_time_utc": datetime.now(timezone.utc).isoformat(),
        "open_count": len(open_trades),
        "closed_count": len(closed_trades),
        "closed_tp_count": len([trade for trade in closed_trades if trade.get("status") == CLOSED_TP]),
        "closed_sl_count": len([trade for trade in closed_trades if trade.get("status") == CLOSED_SL]),
        "total_realized_pnl": total_pnl,
        "total_realized_r": total_r,
        "open_trades": open_trades,
        "closed_trades": closed_trades,
    }
