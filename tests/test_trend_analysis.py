import pandas as pd

from strategy.trend_analysis import analyze_trend


def trend_df(close: float, ema_20: float, ema_50: float, ema_200: float) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "close": [close, close],
            "ema_20": [ema_20, ema_20],
            "ema_50": [ema_50, ema_50],
            "ema_200": [ema_200, ema_200],
            "is_closed_candle": [True, False],
        }
    )


def test_bullish_trend_detection() -> None:
    result = analyze_trend(trend_df(110, 105, 100, 95))
    assert result["trend"] == "bullish"
    assert result["strength"] == "strong"


def test_bearish_trend_detection() -> None:
    result = analyze_trend(trend_df(90, 95, 100, 105))
    assert result["trend"] == "bearish"
    assert result["strength"] == "strong"


def test_neutral_trend_detection() -> None:
    result = analyze_trend(trend_df(100, 105, 95, 98))
    assert result["trend"] == "neutral"
    assert result["strength"] == "weak"
