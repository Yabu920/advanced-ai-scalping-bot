from risk.lot_size import estimate_lot_size, round_volume_to_step


def symbol_info() -> dict:
    return {
        "name": "EURUSDm",
        "point": 0.00001,
        "digits": 5,
        "trade_tick_size": 0.00001,
        "trade_tick_value": 1.0,
        "volume_min": 0.01,
        "volume_max": 100,
        "volume_step": 0.01,
    }


def test_round_volume_to_step() -> None:
    assert round_volume_to_step(0.123, 0.01, 0.01, 100) == 0.12


def test_estimate_lot_size_with_valid_tick_value_tick_size() -> None:
    result = estimate_lot_size("EURUSDm", 1.1000, 1.0990, 10.0, symbol_info())
    assert result["valid"] is True
    assert result["lot_size"] > 0


def test_missing_tick_value_returns_invalid() -> None:
    info = symbol_info()
    info["trade_tick_value"] = None
    result = estimate_lot_size("EURUSDm", 1.1000, 1.0990, 10.0, info)
    assert result["valid"] is False
    assert "Missing tick value/tick size; cannot safely estimate lot size." in result["issues"]
