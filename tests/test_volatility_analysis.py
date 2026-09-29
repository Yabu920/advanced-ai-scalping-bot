import pandas as pd

from strategy.volatility_analysis import analyze_volatility


def volatility_df(latest_atr: float) -> pd.DataFrame:
    atr_values = [10.0] * 50 + [latest_atr]
    return pd.DataFrame(
        {
            "atr_14": atr_values + [latest_atr],
            "candle_range": [1.0] * 52,
            "is_closed_candle": [True] * 51 + [False],
        }
    )


def test_low_volatility_classification() -> None:
    result = analyze_volatility(volatility_df(6.0))
    assert result["volatility"] == "low"


def test_normal_volatility_classification() -> None:
    result = analyze_volatility(volatility_df(10.0))
    assert result["volatility"] == "normal"


def test_high_volatility_classification() -> None:
    result = analyze_volatility(volatility_df(16.0))
    assert result["volatility"] == "high"


def test_extreme_volatility_classification() -> None:
    result = analyze_volatility(volatility_df(25.0))
    assert result["volatility"] == "extreme"
