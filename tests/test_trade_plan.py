from types import SimpleNamespace

from risk.trade_plan import TradePlanBuilder


def settings() -> SimpleNamespace:
    return SimpleNamespace(
        risk_per_trade_percent=0.5,
        max_risk_per_trade_percent=1.0,
        default_rr_ratio=2.0,
        min_rr_ratio=1.5,
        atr_sl_multiplier=1.2,
        atr_tp_multiplier=2.0,
        use_fixed_risk_amount=False,
        fixed_risk_amount=5.0,
        min_stop_atr_multiplier=0.8,
        max_stop_atr_multiplier=3.0,
    )


def account() -> dict:
    return {"equity": 1000, "balance": 1000, "currency": "USD"}


def symbol_info() -> dict:
    return {
        "name": "EURUSDm",
        "trade_tick_size": 0.00001,
        "trade_tick_value": 1.0,
        "volume_min": 0.01,
        "volume_max": 100,
        "volume_step": 0.01,
    }


def signal(status: str = "ELIGIBLE") -> dict:
    return {
        "symbol": "EURUSDm",
        "timeframe": "M1",
        "direction": "BUY",
        "status": status,
        "score": 80,
        "details": {
            "latest_candle": {"close": 1.1000, "atr_14": 0.0010},
            "timeframe_analysis": {"volatility": {"atr_14": 0.0010}},
        },
    }


def test_rejected_signal_creates_invalid_no_executable_plan() -> None:
    plan = TradePlanBuilder(settings()).build_plan(signal("REJECTED"), account(), symbol_info())
    assert plan["valid"] is False
    assert plan["executable_later"] is False


def test_eligible_signal_creates_valid_plan_with_mocked_symbol_info() -> None:
    plan = TradePlanBuilder(settings()).build_plan(signal("ELIGIBLE"), account(), symbol_info())
    assert plan["valid"] is True
    assert plan["executable_later"] is True
    assert plan["lot_size"] > 0


def test_watchlist_signal_creates_preview_but_executable_false() -> None:
    plan = TradePlanBuilder(settings()).build_plan(signal("WATCHLIST"), account(), symbol_info())
    assert plan["valid"] is True
    assert plan["executable_later"] is False
