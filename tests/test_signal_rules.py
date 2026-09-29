import pandas as pd

from strategy.signal_rules import (
    check_ema_alignment,
    check_rsi_confirmation,
    determine_direction_from_bias,
)


def test_bullish_bias_returns_buy() -> None:
    result = determine_direction_from_bias({"bias": "bullish"})
    assert result["direction"] == "BUY"
    assert result["allowed"] is True


def test_bearish_bias_returns_sell() -> None:
    result = determine_direction_from_bias({"bias": "bearish"})
    assert result["direction"] == "SELL"
    assert result["allowed"] is True


def test_mixed_bias_returns_no_trade_when_not_allowed() -> None:
    result = determine_direction_from_bias({"bias": "mixed"}, allow_mixed_bias=False)
    assert result["direction"] == "NO_TRADE"
    assert result["allowed"] is False


def test_buy_ema_alignment_works() -> None:
    row = pd.Series({"close": 105, "ema_20": 100, "ema_50": 95})
    result = check_ema_alignment(row, "BUY")
    assert result["passed"] is True
    assert result["score"] == 20


def test_sell_ema_alignment_works() -> None:
    row = pd.Series({"close": 95, "ema_20": 100, "ema_50": 105})
    result = check_ema_alignment(row, "SELL")
    assert result["passed"] is True
    assert result["score"] == 20


def test_buy_rsi_confirmation_works() -> None:
    result = check_rsi_confirmation(pd.Series({"rsi_14": 55}), "BUY")
    assert result["passed"] is True
    assert result["score"] == 15


def test_sell_rsi_confirmation_works() -> None:
    result = check_rsi_confirmation(pd.Series({"rsi_14": 45}), "SELL")
    assert result["passed"] is True
    assert result["score"] == 15
