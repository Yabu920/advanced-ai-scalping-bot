import pandas as pd

from paper.paper_monitor import (
    calculate_floating_metrics,
    detect_open_trade_price_breach,
    enrich_open_trades_with_market_data,
)


def buy_trade() -> dict:
    return {"direction": "BUY", "entry_price": 100.0, "stop_loss": 95.0, "take_profit": 110.0, "risk_amount": 5.0}


def sell_trade() -> dict:
    return {"direction": "SELL", "entry_price": 100.0, "stop_loss": 105.0, "take_profit": 90.0, "risk_amount": 5.0}


def test_buy_floating_metrics_positive_when_price_above_entry() -> None:
    result = calculate_floating_metrics(buy_trade(), 103.0)
    assert result["floating_r"] > 0
    assert result["floating_pnl_estimate"] > 0


def test_sell_floating_metrics_positive_when_price_below_entry() -> None:
    result = calculate_floating_metrics(sell_trade(), 97.0)
    assert result["floating_r"] > 0
    assert result["floating_pnl_estimate"] > 0


def test_distance_to_tp_and_sl_calculated_correctly() -> None:
    result = calculate_floating_metrics(buy_trade(), 103.0)
    assert result["distance_to_tp"] == 7.0
    assert result["distance_to_sl"] == 8.0


def test_opening_candle_extreme_does_not_warn_for_new_paper_trade() -> None:
    trade = {**sell_trade(), "status": "OPEN", "opened_candle_time": "2026-11-06T14:40:00Z"}
    candle = {"time": pd.Timestamp("2026-11-06T14:40:00Z"), "high": 106.0, "low": 99.0}

    result = detect_open_trade_price_breach(trade, candle)

    assert result["warning"] is False


def test_prior_candle_extreme_does_not_warn_for_open_trade() -> None:
    trade = {**sell_trade(), "status": "OPEN", "opened_candle_time": "2026-11-06T14:40:00Z"}
    candle = {"time": "2026-11-06T14:35:00Z", "high": 106.0, "low": 99.0}

    assert detect_open_trade_price_breach(trade, candle)["warning"] is False


def test_later_candle_breach_still_warns_for_unclosed_paper_trade() -> None:
    trade = {**sell_trade(), "status": "OPEN", "opened_candle_time": "2026-11-06T14:40:00Z"}
    candle = {"time": "2026-11-06T14:45:00Z", "high": 106.0, "low": 99.0}

    result = detect_open_trade_price_breach(trade, candle)

    assert result["warning"] is True
    assert result["breach_type"] == "SL"


def test_missing_opened_time_cannot_claim_price_breach() -> None:
    trade = {**sell_trade(), "status": "OPEN"}
    candle = {"time": "2026-11-06T14:45:00Z", "high": 106.0, "low": 99.0}

    assert detect_open_trade_price_breach(trade, candle)["warning"] is False


def test_enriched_new_trade_ignores_opening_candle_extreme() -> None:
    trade = {
        **sell_trade(), "status": "OPEN", "symbol": "EURUSD", "timeframe": "M5",
        "opened_candle_time": "2026-11-06T14:40:00Z",
    }
    data = {"EURUSD": {"M5": pd.DataFrame([
        {"time": pd.Timestamp("2026-11-06T14:40:00Z"), "high": 106.0, "low": 99.0,
         "close": 100.0, "is_closed_candle": True},
        {"time": pd.Timestamp("2026-11-06T14:45:00Z"), "high": 101.0, "low": 99.0,
         "close": 100.0, "is_closed_candle": False},
    ])}}

    result = enrich_open_trades_with_market_data([trade], data)

    assert result[0]["execution_warning"]["warning"] is False
