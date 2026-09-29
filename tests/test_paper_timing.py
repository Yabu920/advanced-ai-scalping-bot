from types import SimpleNamespace

import pandas as pd

from paper.paper_engine import PaperExecutionEngine
from paper.paper_trade import CLOSED_SL, CLOSED_TP, OPEN, build_paper_trade_from_plan


def settings() -> SimpleNamespace:
    return SimpleNamespace()


def valid_plan(latest_time: str = "2026-05-20T10:00:00+00:00") -> dict:
    return {
        "symbol": "EURUSDm",
        "timeframe": "M1",
        "direction": "BUY",
        "signal_status": "ELIGIBLE",
        "signal_score": 80,
        "valid": True,
        "entry_reference": 100.0,
        "stop_loss": 95.0,
        "take_profit": 110.0,
        "lot_size": 0.1,
        "risk_amount": 5.0,
        "risk_percent": 0.5,
        "rr_ratio": 2.0,
        "latest_time": latest_time,
    }


def trade(direction: str = "BUY") -> dict:
    return {
        "paper_trade_id": "paper-1",
        "created_time_utc": "2026-05-20T10:00:00+00:00",
        "opened_candle_time": "2026-05-20T10:00:00+00:00",
        "signal_candle_time": "2026-05-20T10:00:00+00:00",
        "last_evaluated_candle_time": "2026-05-20T10:00:00+00:00",
        "symbol": "EURUSDm",
        "timeframe": "M1",
        "direction": direction,
        "status": OPEN,
        "entry_price": 100.0,
        "stop_loss": 95.0 if direction == "BUY" else 105.0,
        "take_profit": 110.0 if direction == "BUY" else 90.0,
        "risk_amount": 5.0,
        "rr_ratio": 2.0,
        "issues": [],
    }


def candle(time: str, high: float, low: float) -> dict:
    return {"time": time, "high": high, "low": low, "is_closed_candle": True}


def test_paper_trade_includes_opened_candle_time_when_plan_has_latest_time() -> None:
    result = build_paper_trade_from_plan(valid_plan(), {"plan_valid": True})
    assert result["opened_candle_time"] == "2026-05-20T10:00:00+00:00"
    assert result["signal_candle_time"] == "2026-05-20T10:00:00+00:00"
    assert result["last_evaluated_candle_time"] == "2026-05-20T10:00:00+00:00"


def test_update_does_not_close_using_candle_before_opened_candle_time() -> None:
    result = PaperExecutionEngine(settings()).update_open_trade_with_candles(
        trade("BUY"),
        [candle("2026-05-20T09:59:00+00:00", 111.0, 94.0)],
    )
    assert result["status"] == OPEN


def test_update_does_not_close_using_candle_equal_to_opened_candle_time() -> None:
    result = PaperExecutionEngine(settings()).update_open_trade_with_candles(
        trade("BUY"),
        [candle("2026-05-20T10:00:00+00:00", 111.0, 94.0)],
    )
    assert result["status"] == OPEN


def test_update_closes_using_first_valid_candle_after_opened_candle_time() -> None:
    result = PaperExecutionEngine(settings()).update_open_trade_with_candles(
        trade("BUY"),
        [candle("2026-05-20T10:01:00+00:00", 111.0, 99.0)],
    )
    assert result["status"] == CLOSED_TP
    assert result["close_time_utc"] == "2026-05-20T10:01:00"


def test_update_scans_multiple_candles_and_catches_hit_between_runs() -> None:
    result = PaperExecutionEngine(settings()).update_open_trade_with_candles(
        trade("BUY"),
        [
            candle("2026-05-20T10:01:00+00:00", 103.0, 99.0),
            candle("2026-05-20T10:02:00+00:00", 111.0, 99.0),
        ],
    )
    assert result["status"] == CLOSED_TP
    assert result["close_time_utc"] == "2026-05-20T10:02:00"


def test_last_evaluated_candle_time_is_updated_when_trade_remains_open() -> None:
    result = PaperExecutionEngine(settings()).update_open_trade_with_candles(
        trade("BUY"),
        [
            candle("2026-05-20T10:01:00+00:00", 103.0, 99.0),
            candle("2026-05-20T10:02:00+00:00", 104.0, 98.0),
        ],
    )
    assert result["status"] == OPEN
    assert result["last_evaluated_candle_time"] == "2026-05-20T10:02:00"


def test_close_time_is_never_earlier_than_opened_candle_time() -> None:
    result = PaperExecutionEngine(settings()).update_open_trade_with_candles(
        trade("BUY"),
        [
            candle("2026-05-20T09:59:00+00:00", 111.0, 99.0),
            candle("2026-05-20T10:01:00+00:00", 111.0, 99.0),
        ],
    )
    close_time = pd.Timestamp(result["close_time_utc"])
    opened_time = pd.Timestamp(result["opened_candle_time"]).tz_convert("UTC").tz_localize(None)
    assert close_time > opened_time


def test_same_candle_tp_sl_after_entry_closes_as_sl_conservative() -> None:
    result = PaperExecutionEngine(settings()).update_open_trade_with_candles(
        trade("BUY"),
        [candle("2026-05-20T10:01:00+00:00", 111.0, 94.0)],
    )
    assert result["status"] == CLOSED_SL
    assert result["close_reason"] == "Both TP and SL touched in same candle; conservative SL-first assumption."
