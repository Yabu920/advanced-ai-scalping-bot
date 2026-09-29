from strategy.market_regime import classify_market_regime


def test_bad_spread_returns_tradable_false() -> None:
    result = classify_market_regime(
        {"trend": "bullish"},
        {"volatility": "normal"},
        {"spread_quality": "high"},
    )
    assert result["regime"] == "BAD_SPREAD"
    assert result["tradable"] is False


def test_trending_returns_tradable_true() -> None:
    result = classify_market_regime(
        {"trend": "bullish"},
        {"volatility": "normal"},
        {"spread_quality": "good"},
    )
    assert result["regime"] == "TRENDING"
    assert result["tradable"] is True


def test_low_volatility_returns_tradable_false() -> None:
    result = classify_market_regime(
        {"trend": "bullish"},
        {"volatility": "low"},
        {"spread_quality": "good"},
    )
    assert result["regime"] == "LOW_VOLATILITY"
    assert result["tradable"] is False
