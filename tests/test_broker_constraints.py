from types import SimpleNamespace

from risk.broker_constraints import validate_stop_and_tp_distance, validate_trade_mode, validate_volume_constraints


def settings() -> SimpleNamespace:
    return SimpleNamespace(min_stop_distance_points=0, min_tp_distance_points=0)


def symbol_info() -> dict:
    return {
        "point": 0.00001,
        "volume_min": 0.01,
        "volume_max": 10.0,
        "volume_step": 0.01,
        "trade_stops_level": 5,
        "trade_freeze_level": 2,
        "trade_mode": 4,
    }


def plan() -> dict:
    return {"entry_reference": 1.1000, "stop_loss": 1.0990, "take_profit": 1.1020, "lot_size": 0.10}


def test_valid_stop_tp_distance_passes() -> None:
    result = validate_stop_and_tp_distance(plan(), symbol_info(), settings())
    assert result["valid"] is True
    assert result["warnings"]


def test_stop_distance_too_small_fails() -> None:
    bad = plan()
    bad["stop_loss"] = 1.09999
    result = validate_stop_and_tp_distance(bad, symbol_info(), settings())
    assert result["valid"] is False


def test_volume_below_min_fails() -> None:
    bad = plan()
    bad["lot_size"] = 0.001
    assert validate_volume_constraints(bad, symbol_info())["valid"] is False


def test_volume_above_max_fails() -> None:
    bad = plan()
    bad["lot_size"] = 20
    assert validate_volume_constraints(bad, symbol_info())["valid"] is False


def test_trade_mode_unknown_returns_warning_but_not_crash() -> None:
    info = symbol_info()
    info["trade_mode"] = None
    result = validate_trade_mode(info)
    assert result["valid"] is True
    assert result["warnings"]
