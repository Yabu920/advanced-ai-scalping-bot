from strategy.spread_analysis import analyze_spread


def test_xauusd_high_spread_classification() -> None:
    result = analyze_spread("XAUUSDm", 200, 4.0)
    assert result["spread_quality"] == "high"


def test_eurusd_good_spread_classification() -> None:
    result = analyze_spread("EURUSDm", 12, 0.001)
    assert result["spread_quality"] == "good"
