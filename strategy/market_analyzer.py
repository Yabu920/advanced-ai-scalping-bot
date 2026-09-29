"""High-level market analyzer for Stage 3 diagnostics."""

from __future__ import annotations

from typing import Any

import pandas as pd

from strategy.data_validation import validate_ohlc_dataframe
from strategy.indicators import add_full_indicators
from strategy.market_regime import classify_market_regime
from strategy.spread_analysis import analyze_spread
from strategy.trend_analysis import analyze_multi_timeframe_bias, analyze_trend
from strategy.volatility_analysis import analyze_volatility


FULL_INDICATOR_COLUMNS = [
    "ema_20",
    "ema_50",
    "ema_200",
    "rsi_14",
    "atr_14",
    "candle_body",
    "candle_range",
    "upper_wick",
    "lower_wick",
    "body_to_range_ratio",
]


class MarketAnalyzer:
    """Analyze trend, volatility, spread, and regime from collected market data."""

    def analyze_timeframe(
        self,
        symbol: str,
        timeframe: str,
        df: pd.DataFrame,
        spread_points: float | None = None,
    ) -> dict[str, Any]:
        if not all(column in df.columns for column in FULL_INDICATOR_COLUMNS):
            df = add_full_indicators(df)

        validation = validate_ohlc_dataframe(df)
        trend = analyze_trend(df)
        volatility = analyze_volatility(df)
        spread = analyze_spread(symbol, spread_points, volatility.get("atr_14"))
        regime = classify_market_regime(trend, volatility, spread)

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "valid": validation["valid"],
            "validation": validation,
            "trend": trend,
            "volatility": volatility,
            "spread": spread,
            "regime": regime,
        }

    def analyze_symbol(
        self,
        symbol: str,
        symbol_data: dict[str, pd.DataFrame],
        spread_points: float | None = None,
    ) -> dict[str, Any]:
        analyzed_frames: dict[str, dict[str, Any]] = {}
        indicator_data: dict[str, pd.DataFrame] = {}

        for timeframe, df in symbol_data.items():
            enriched = df if all(column in df.columns for column in FULL_INDICATOR_COLUMNS) else add_full_indicators(df)
            indicator_data[timeframe] = enriched
            analyzed_frames[timeframe] = self.analyze_timeframe(symbol, timeframe, enriched, spread_points)

        return {
            "symbol": symbol,
            "timeframes": analyzed_frames,
            "multi_timeframe_bias": analyze_multi_timeframe_bias(indicator_data),
        }

    def analyze_market(
        self,
        data: dict[str, dict[str, pd.DataFrame]],
        spread_map: dict[str, float | None] | None = None,
    ) -> dict[str, Any]:
        spreads = spread_map or {}
        return {
            symbol: self.analyze_symbol(symbol, symbol_data, spreads.get(symbol))
            for symbol, symbol_data in data.items()
        }
