from types import SimpleNamespace

from risk.pre_execution_validator import PreExecutionValidator


def settings() -> SimpleNamespace:
    return SimpleNamespace(
        allow_watchlist_plan_preview=True,
        require_eligible_signal_for_execution=True,
        check_margin_requirement=True,
        min_stop_distance_points=0,
        min_tp_distance_points=0,
        max_spread_to_atr_ratio=0.5,
        max_spread_cost_risk_percent=50.0,
        max_spread_to_sl_ratio=0.5,
        max_spread_to_tp_ratio=0.3,
        min_net_rr_after_spread=1.2,
    )


def plan(status: str = "ELIGIBLE") -> dict:
    return {
        "symbol": "EURUSDm",
        "timeframe": "M1",
        "direction": "SELL",
        "signal_status": status,
        "valid": status != "REJECTED",
        "entry_reference": 1.1000,
        "atr_reference": 0.001,
        "stop_loss": 1.1010,
        "take_profit": 1.0980,
        "lot_size": 0.10,
        "risk_amount": 10.0,
        "issues": [],
    }


def symbol_info() -> dict:
    return {
        "point": 0.00001,
        "volume_min": 0.01,
        "volume_max": 10.0,
        "volume_step": 0.01,
        "trade_stops_level": 5,
        "trade_mode": 4,
        "trade_tick_size": 0.00001,
        "trade_tick_value": 1.0,
        "margin_initial": 100,
    }


def test_watchlist_plan_preview_only_and_not_execution_ready() -> None:
    result = PreExecutionValidator().validate_plan(plan("WATCHLIST"), symbol_info(), {"margin_free": 1000}, 10, settings())
    assert result["preview_only"] is True
    assert result["execution_ready_later"] is False


def test_rejected_plan_is_invalid() -> None:
    result = PreExecutionValidator().validate_plan(plan("REJECTED"), symbol_info(), {"margin_free": 1000}, 10, settings())
    assert result["execution_ready_later"] is False
    assert result["issues"]


def test_eligible_valid_plan_can_be_execution_ready_later_true() -> None:
    result = PreExecutionValidator().validate_plan(plan("ELIGIBLE"), symbol_info(), {"margin_free": 1000}, 10, settings())
    assert result["execution_ready_later"] is True


def test_high_trading_cost_makes_execution_ready_later_false() -> None:
    result = PreExecutionValidator().validate_plan(plan("ELIGIBLE"), symbol_info(), {"margin_free": 1000}, 100, settings())
    assert result["costs_valid"] is False
    assert result["execution_ready_later"] is False
