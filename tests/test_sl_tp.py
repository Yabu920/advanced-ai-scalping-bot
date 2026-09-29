from risk.sl_tp import build_sl_tp_prices, validate_sl_tp


def test_buy_sl_tp_valid() -> None:
    prices = build_sl_tp_prices("BUY", 100, 10, 2)
    assert prices["stop_loss"] == 90
    assert prices["take_profit"] == 120
    assert validate_sl_tp("BUY", 100, prices["stop_loss"], prices["take_profit"])["valid"] is True


def test_sell_sl_tp_valid() -> None:
    prices = build_sl_tp_prices("SELL", 100, 10, 2)
    assert prices["stop_loss"] == 110
    assert prices["take_profit"] == 80
    assert validate_sl_tp("SELL", 100, prices["stop_loss"], prices["take_profit"])["valid"] is True


def test_invalid_sl_tp_detected() -> None:
    result = validate_sl_tp("BUY", 100, 105, 120)
    assert result["valid"] is False
    assert result["issues"]
