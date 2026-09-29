from types import SimpleNamespace

import pandas as pd

from paper.paper_engine import PaperExecutionEngine
from paper.paper_trade import CLOSED_SL, CLOSED_TP, OPEN
from paper.paper_monitor import detect_open_trade_price_breach


def settings() -> SimpleNamespace:
    return SimpleNamespace()


def trade(direction: str = "BUY", last_evaluated: str | None = "2026-06-09T14:05:00+00:00") -> dict:
    return {
        "paper_trade_id": "paper-test",
        "created_time_utc": "2026-06-09T20:10:14+00:00",
        "opened_candle_time": "2026-06-09T14:05:00+00:00",
        "signal_candle_time": "2026-06-09T14:05:00+00:00",
        "last_evaluated_candle_time": last_evaluated,
        "symbol": "GBPUSDm",
        "timeframe": "M5",
        "direction": direction,
        "status": OPEN,
        "entry_price": 1.34066 if direction == "BUY" else 1.34066,
        "stop_loss": 1.34002 if direction == "BUY" else 1.34120,
        "take_profit": 1.34195 if direction == "BUY" else 1.33920,
        "risk_amount": 5.0,
        "rr_ratio": 2.0,
        "issues": [],
    }


def candle(time: str, high: float, low: float) -> dict:
    return {"time": time, "high": high, "low": low, "close": (high + low) / 2, "is_closed_candle": True}


def df(candles: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(candles)


def test_buy_trade_closes_sl_when_later_closed_candle_low_is_below_sl() -> None:
    result = PaperExecutionEngine(settings()).update_open_trade_with_candles(
        trade("BUY"),
        [candle("2026-06-09T14:10:00+00:00", 1.34090, 1.33990)],
    )
    assert result["status"] == CLOSED_SL


def test_buy_trade_closes_tp_when_later_closed_candle_high_is_above_tp() -> None:
    result = PaperExecutionEngine(settings()).update_open_trade_with_candles(
        trade("BUY"),
        [candle("2026-06-09T14:10:00+00:00", 1.34200, 1.34040)],
    )
    assert result["status"] == CLOSED_TP


def test_sell_trade_closes_sl_when_later_closed_candle_high_is_above_sl() -> None:
    result = PaperExecutionEngine(settings()).update_open_trade_with_candles(
        trade("SELL"),
        [candle("2026-06-09T14:10:00+00:00", 1.34130, 1.34020)],
    )
    assert result["status"] == CLOSED_SL


def test_sell_trade_closes_tp_when_later_closed_candle_low_is_below_tp() -> None:
    result = PaperExecutionEngine(settings()).update_open_trade_with_candles(
        trade("SELL"),
        [candle("2026-06-09T14:10:00+00:00", 1.34080, 1.33900)],
    )
    assert result["status"] == CLOSED_TP


def test_missing_last_evaluated_scans_all_candles_after_opened_time() -> None:
    result = PaperExecutionEngine(settings()).update_open_trade_with_candles(
        trade("BUY", last_evaluated=None),
        [
            candle("2026-06-09T14:00:00+00:00", 1.34200, 1.33900),
            candle("2026-06-09T14:10:00+00:00", 1.34080, 1.33990),
        ],
    )
    assert result["status"] == CLOSED_SL
    assert result["close_time_utc"] == "2026-06-09T14:10:00"


def test_last_evaluated_before_sl_candle_closes_correctly() -> None:
    result = PaperExecutionEngine(settings()).update_open_trade_with_candles(
        trade("BUY", last_evaluated="2026-06-09T14:10:00+00:00"),
        [candle("2026-06-09T14:15:00+00:00", 1.34080, 1.33990)],
    )
    assert result["status"] == CLOSED_SL


def test_last_evaluated_does_not_skip_sl_candle_from_dataframe_scan() -> None:
    engine = PaperExecutionEngine(settings())
    open_trade = trade("BUY", last_evaluated="2026-06-09T14:05:00+00:00")
    market_data = {
        "GBPUSDm": {
            "M5": df(
                [
                    candle("2026-06-09T14:05:00+00:00", 1.34090, 1.34020),
                    candle("2026-06-09T14:10:00+00:00", 1.34080, 1.33990),
                    candle("2026-06-09T14:15:00+00:00", 1.34070, 1.33980),
                ]
            )
        }
    }
    result = engine.update_open_trades([open_trade], market_data)[0]
    assert result["status"] == CLOSED_SL
    assert result["close_time_utc"] == "2026-06-09T14:10:00"


def test_same_candle_hits_tp_and_sl_uses_closed_sl() -> None:
    result = PaperExecutionEngine(settings()).update_open_trade_with_candles(
        trade("BUY"),
        [candle("2026-06-09T14:10:00+00:00", 1.34200, 1.33990)],
    )
    assert result["status"] == CLOSED_SL


def test_trade_cannot_remain_open_if_latest_valid_post_entry_candle_crossed_sl() -> None:
    engine = PaperExecutionEngine(settings())
    open_trade = trade("BUY", last_evaluated="2026-06-09T14:10:00+00:00")
    latest = candle("2026-06-09T14:10:00+00:00", 1.34080, 1.33990)
    result = engine.recover_open_trade_if_latest_candle_breached(open_trade, latest)
    assert result["status"] == CLOSED_SL
    assert "Recovered close from latest closed candle breach after previous evaluation skip." in result["issues"]


def test_status_warning_detects_open_trade_beyond_sl() -> None:
    result = detect_open_trade_price_breach(
        trade("BUY"),
        candle("2026-06-09T14:10:00+00:00", 1.34080, 1.33990),
    )
    assert result["warning"] is True
    assert result["breach_type"] == "SL"
