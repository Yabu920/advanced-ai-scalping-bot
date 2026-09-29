from types import SimpleNamespace

import pandas as pd

from strategy.setup_scoring import score_setup


def settings(min_score: int = 70, watch_score: int = 55, allow_mixed: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        min_signal_score=min_score,
        watchlist_score=watch_score,
        allow_mixed_bias=allow_mixed,
    )


def sample_df(direction: str = "BUY") -> pd.DataFrame:
    if direction == "BUY":
        row = {"close": 105, "ema_20": 100, "ema_50": 95, "rsi_14": 55}
    else:
        row = {"close": 95, "ema_20": 100, "ema_50": 105, "rsi_14": 45}
    return pd.DataFrame([{**row, "is_closed_candle": True}, {**row, "is_closed_candle": False}])


def analysis(regime: str = "TRENDING", tradable: bool = True, volatility: str = "normal") -> dict:
    return {
        "regime": {"regime": regime, "tradable": tradable},
        "volatility": {"volatility": volatility},
    }


def bias(value: str = "bullish", confidence: int = 90) -> dict:
    return {"bias": value, "confidence": confidence}


def test_bad_spread_causes_rejected() -> None:
    result = score_setup("XAUUSDm", "M1", sample_df(), analysis("BAD_SPREAD", False), bias(), settings())
    assert result["status"] == "REJECTED"
    assert "BAD_SPREAD" in result["rejection_reasons"]


def test_low_volatility_causes_rejected() -> None:
    result = score_setup("GBPUSDm", "M5", sample_df("SELL"), analysis("LOW_VOLATILITY", False, "low"), bias("bearish"), settings())
    assert result["status"] == "REJECTED"
    assert "LOW_VOLATILITY" in result["rejection_reasons"]


def test_extreme_volatility_cannot_become_eligible_from_score() -> None:
    result = score_setup(
        "EURUSDm",
        "M5",
        sample_df(),
        analysis("HIGH_VOLATILITY", False, "extreme"),
        bias("bullish", 100),
        settings(),
    )

    assert result["score"] >= result["max_score"] * 0.70
    assert result["status"] == "REJECTED"
    assert "EXTREME_VOLATILITY" in result["rejection_reasons"]


def test_any_non_tradable_regime_cannot_become_eligible_from_score() -> None:
    result = score_setup(
        "EURUSDm",
        "M5",
        sample_df(),
        analysis("UNKNOWN", False, "unknown"),
        bias("bullish", 100),
        settings(),
    )

    assert result["score"] >= result["max_score"] * 0.70
    assert result["status"] == "REJECTED"
    assert "TIMEFRAME_NOT_TRADABLE" in result["rejection_reasons"]


def test_strong_bullish_setup_can_become_eligible() -> None:
    result = score_setup("EURUSDm", "M1", sample_df(), analysis(), bias("bullish", 90), settings())
    assert result["status"] == "ELIGIBLE"
    assert result["direction"] == "BUY"


def test_mixed_bias_rejected_when_not_allowed() -> None:
    result = score_setup("EURUSDm", "M1", sample_df(), analysis(), bias("mixed", 40), settings())
    assert result["status"] == "REJECTED"
    assert "MIXED_BIAS" in result["rejection_reasons"]


def test_watchlist_score_becomes_watchlist() -> None:
    weak_df = pd.DataFrame(
        [
            {"close": 95, "ema_20": 100, "ema_50": 110, "rsi_14": 50, "is_closed_candle": True},
            {"close": 95, "ema_20": 100, "ema_50": 110, "rsi_14": 50, "is_closed_candle": False},
        ]
    )
    result = score_setup("EURUSDm", "M1", weak_df, analysis(), bias("bullish", 40), settings())
    assert result["status"] == "WATCHLIST"
    assert 55 <= result["score"] < 70
