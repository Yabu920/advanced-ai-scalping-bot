"""Pure indicator calculations for candle data."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"DataFrame missing required columns: {missing}")


def ema(series: pd.Series, period: int) -> pd.Series:
    if period <= 0:
        raise ValueError("EMA period must be greater than zero.")
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    if period <= 0:
        raise ValueError("RSI period must be greater than zero.")

    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_values = 100 - (100 / (1 + rs))
    rsi_values = rsi_values.mask((avg_loss == 0) & (avg_gain > 0), 100)
    rsi_values = rsi_values.mask((avg_loss == 0) & (avg_gain == 0), 50)
    return rsi_values.fillna(50)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    if period <= 0:
        raise ValueError("ATR period must be greater than zero.")
    if df.empty:
        return pd.Series(dtype="float64", index=df.index)

    _require_columns(df, ["high", "low", "close"])

    high_low = df["high"] - df["low"]
    high_previous_close = (df["high"] - df["close"].shift(1)).abs()
    low_previous_close = (df["low"] - df["close"].shift(1)).abs()

    true_range = pd.concat([high_low, high_previous_close, low_previous_close], axis=1).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def add_basic_indicators(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    if result.empty:
        for column in ["ema_20", "ema_50", "ema_200", "rsi_14", "atr_14"]:
            result[column] = pd.Series(dtype="float64")
        return result

    _require_columns(result, ["high", "low", "close"])

    result["ema_20"] = ema(result["close"], 20)
    result["ema_50"] = ema(result["close"], 50)
    result["ema_200"] = ema(result["close"], 200)
    result["rsi_14"] = rsi(result["close"], 14)
    result["atr_14"] = atr(result, 14)
    return result


def candle_body(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype="float64", index=df.index)
    _require_columns(df, ["open", "close"])
    return (df["close"] - df["open"]).abs()


def candle_range(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype="float64", index=df.index)
    _require_columns(df, ["high", "low"])
    return df["high"] - df["low"]


def upper_wick(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype="float64", index=df.index)
    _require_columns(df, ["open", "high", "close"])
    candle_top = pd.concat([df["open"], df["close"]], axis=1).max(axis=1)
    return df["high"] - candle_top


def lower_wick(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype="float64", index=df.index)
    _require_columns(df, ["open", "low", "close"])
    candle_bottom = pd.concat([df["open"], df["close"]], axis=1).min(axis=1)
    return candle_bottom - df["low"]


def add_candle_features(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    if result.empty:
        for column in [
            "candle_body",
            "candle_range",
            "upper_wick",
            "lower_wick",
            "body_to_range_ratio",
        ]:
            result[column] = pd.Series(dtype="float64")
        return result

    _require_columns(result, ["open", "high", "low", "close"])
    result["candle_body"] = candle_body(result)
    result["candle_range"] = candle_range(result)
    result["upper_wick"] = upper_wick(result)
    result["lower_wick"] = lower_wick(result)
    result["body_to_range_ratio"] = result["candle_body"] / result["candle_range"].replace(0, np.nan)
    result["body_to_range_ratio"] = result["body_to_range_ratio"].fillna(0)
    return result


def add_full_indicators(df: pd.DataFrame) -> pd.DataFrame:
    result = add_basic_indicators(df)
    return add_candle_features(result)
