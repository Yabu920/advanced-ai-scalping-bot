from types import SimpleNamespace

from risk.trading_costs import (
    calculate_net_rr_after_spread,
    calculate_spread_ratios,
    estimate_spread_cost,
    validate_trading_costs,
)


def symbol_info() -> dict:
    return {"point": 0.00001, "trade_tick_size": 0.00001, "trade_tick_value": 1.0}


def plan() -> dict:
    return {
        "entry_reference": 1.1000,
        "stop_loss": 1.0990,
        "take_profit": 1.1020,
        "lot_size": 0.10,
        "risk_amount": 10.0,
    }


def settings() -> SimpleNamespace:
    return SimpleNamespace(
        max_spread_to_atr_ratio=0.25,
        max_spread_cost_risk_percent=20.0,
        max_spread_to_sl_ratio=0.35,
        max_spread_to_tp_ratio=0.25,
        min_net_rr_after_spread=1.2,
    )


def test_spread_cost_known_with_tick_info() -> None:
    result = estimate_spread_cost(plan(), symbol_info(), 10)
    assert result["known"] is True
    assert result["spread_cost"] == 1.0


def test_spread_cost_unknown_without_tick_info() -> None:
    result = estimate_spread_cost(plan(), {"point": 0.00001}, 10)
    assert result["known"] is False
    assert result["issues"]


def test_spread_to_sl_tp_ratio_calculation() -> None:
    result = calculate_spread_ratios(plan(), symbol_info(), 10, 0.001)
    assert round(result["spread_to_sl_ratio"], 2) == 0.10
    assert round(result["spread_to_tp_ratio"], 2) == 0.05


def test_net_rr_after_spread_calculation() -> None:
    result = calculate_net_rr_after_spread(plan(), symbol_info(), 10)
    assert result["known"] is True
    assert round(result["net_rr_after_spread"], 2) == 1.90


def test_high_spread_to_atr_ratio_fails_validation() -> None:
    result = validate_trading_costs(plan(), symbol_info(), 100, 0.001, settings())
    assert result["valid"] is False
    assert any("Spread/ATR" in issue for issue in result["issues"])


def test_unknown_spread_cost_fails_closed() -> None:
    result = validate_trading_costs(plan(), {"point": 0.00001}, 10, 0.001, settings())
    assert result["valid"] is False
    assert any("tick value/tick size" in issue for issue in result["issues"])
