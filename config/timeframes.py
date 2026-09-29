"""Timeframe conversion helpers for MetaTrader 5."""

from __future__ import annotations

import MetaTrader5 as mt5

TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}

TIMEFRAME_SECONDS = {
    "M1": 60,
    "M5": 5 * 60,
    "M15": 15 * 60,
    "M30": 30 * 60,
    "H1": 60 * 60,
    "H4": 4 * 60 * 60,
    "D1": 24 * 60 * 60,
}


def get_timeframe(value: str) -> int:
    key = value.strip().upper()
    if key not in TIMEFRAMES:
        valid = ", ".join(TIMEFRAMES)
        raise ValueError(f"Unsupported timeframe '{value}'. Supported values: {valid}")
    return TIMEFRAMES[key]


def get_timeframe_seconds(value: str) -> int:
    key = value.strip().upper()
    if key not in TIMEFRAME_SECONDS:
        valid = ", ".join(TIMEFRAME_SECONDS)
        raise ValueError(f"Unsupported timeframe '{value}'. Supported values: {valid}")
    return TIMEFRAME_SECONDS[key]


def timeframe_to_string(value: int) -> str:
    for name, mt5_value in TIMEFRAMES.items():
        if value == mt5_value:
            return name
    return str(value)
