"""Stage 4 signal candidate engine."""

from __future__ import annotations

from typing import Any

import pandas as pd

from strategy.setup_scoring import score_setup


BIAS_WEIGHTS = {"H1": 40, "M15": 30, "M5": 20, "M1": 10}


class SignalEngine:
    """Generate explained signal candidates without placing trades."""

    def generate_symbol_signals(
        self,
        symbol: str,
        symbol_data: dict[str, pd.DataFrame],
        symbol_analysis: dict[str, Any],
        settings: Any,
    ) -> dict[str, Any]:
        bias = self._bias_for_configured_timeframes(
            symbol_analysis.get("multi_timeframe_bias", {}),
            settings.bias_timeframes,
        )
        signals: dict[str, dict[str, Any]] = {}

        for timeframe in settings.signal_timeframes:
            timeframe_key = timeframe.upper()
            df = symbol_data.get(timeframe_key)
            timeframe_analysis = symbol_analysis.get("timeframes", {}).get(timeframe_key)
            if df is None or timeframe_analysis is None:
                signals[timeframe_key] = self._missing_signal(symbol, timeframe_key, bias)
                continue
            signals[timeframe_key] = score_setup(
                symbol,
                timeframe_key,
                df,
                timeframe_analysis,
                bias,
                settings,
            )

        return {
            "symbol": symbol,
            "bias": bias,
            "signals": signals,
        }

    def generate_market_signals(
        self,
        data: dict[str, dict[str, pd.DataFrame]],
        analysis: dict[str, Any],
        settings: Any,
    ) -> dict[str, Any]:
        return {
            symbol: self.generate_symbol_signals(symbol, symbol_data, analysis.get(symbol, {}), settings)
            for symbol, symbol_data in data.items()
        }

    def _bias_for_configured_timeframes(
        self,
        bias: dict[str, Any],
        bias_timeframes: list[str],
    ) -> dict[str, Any]:
        all_trends = bias.get("timeframe_trends", {})
        selected = {
            timeframe.upper(): all_trends[timeframe.upper()]
            for timeframe in bias_timeframes
            if timeframe.upper() in all_trends
        }
        if not selected:
            return {
                "bias": "neutral",
                "confidence": 0,
                "timeframe_trends": {},
                "reason": "No configured bias timeframe analysis is available.",
            }

        bullish_score = 0
        bearish_score = 0
        neutral_score = 0
        for timeframe, trend_result in selected.items():
            weight = BIAS_WEIGHTS.get(timeframe, 0)
            trend = trend_result.get("trend")
            if trend == "bullish":
                bullish_score += weight
            elif trend == "bearish":
                bearish_score += weight
            else:
                neutral_score += weight

        h1_trend = selected.get("H1", {}).get("trend")
        m15_trend = selected.get("M15", {}).get("trend")
        if h1_trend == "bullish" and m15_trend == "bullish":
            bias_name = "bullish"
            confidence = bullish_score
            reason = "Configured H1 and M15 bias are bullish."
        elif h1_trend == "bearish" and m15_trend == "bearish":
            bias_name = "bearish"
            confidence = bearish_score
            reason = "Configured H1 and M15 bias are bearish."
        elif bullish_score > 0 and bearish_score > 0:
            bias_name = "mixed"
            confidence = max(bullish_score, bearish_score)
            reason = "Configured bias timeframes conflict."
        elif neutral_score >= max(bullish_score, bearish_score):
            bias_name = "neutral"
            confidence = neutral_score
            reason = "Configured bias timeframes are mostly neutral."
        elif bullish_score > bearish_score:
            bias_name = "bullish"
            confidence = bullish_score
            reason = "Configured bias timeframes lean bullish."
        else:
            bias_name = "bearish"
            confidence = bearish_score
            reason = "Configured bias timeframes lean bearish."

        return {
            "bias": bias_name,
            "confidence": int(min(confidence, 100)),
            "timeframe_trends": selected,
            "reason": reason,
        }

    def _missing_signal(self, symbol: str, timeframe: str, bias: dict[str, Any]) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": "NO_TRADE",
            "status": "REJECTED",
            "score": 0,
            "max_score": 100,
            "passed_conditions": [],
            "failed_conditions": [f"No data or analysis available for {timeframe}."],
            "rejection_reasons": ["INSUFFICIENT_DATA"],
            "details": {"bias": bias},
        }
