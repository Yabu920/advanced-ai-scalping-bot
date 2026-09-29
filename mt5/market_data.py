"""Market data collection from MetaTrader 5."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import MetaTrader5 as mt5
import pandas as pd

from config.symbols import normalize_symbol
from config.timeframes import get_timeframe, get_timeframe_seconds
from utils.logger import setup_logger

REQUIRED_RATE_COLUMNS = ["time", "open", "high", "low", "close", "tick_volume", "spread"]
HISTORY_SYNC_ATTEMPTS = 5
HISTORY_SYNC_DELAY_SECONDS = 0.5
MAX_LIVE_TICK_AGE_SECONDS = 5 * 60


def _value(source: Any, key: str) -> Any:
    if isinstance(source, dict):
        return source.get(key)
    value = getattr(source, key, None)
    if value is not None:
        return value
    try:
        return source[key]
    except (IndexError, KeyError, TypeError, ValueError):
        return None


def rates_are_fresh(rates: Any, tick: Any, timeframe: str, current_time: float | None = None) -> bool:
    """Compare the newest candle with the broker's latest tick, not wall time.

    Broker tick time detects candles trailing current quotes. Wall-clock tick
    age also rejects an entirely stale cache or a closed market, which is the
    conservative behavior required by the live paper runner.
    """
    if rates is None or len(rates) == 0 or tick is None:
        return False
    latest_rate_time = _value(rates[-1], "time")
    latest_tick_time = _value(tick, "time")
    try:
        lag_seconds = float(latest_tick_time) - float(latest_rate_time)
        tick_age_seconds = (time.time() if current_time is None else current_time) - float(latest_tick_time)
    except (TypeError, ValueError):
        return False
    maximum_lag = max(180, 2 * get_timeframe_seconds(timeframe))
    tick_is_live = -60 <= tick_age_seconds <= MAX_LIVE_TICK_AGE_SECONDS
    return tick_is_live and -get_timeframe_seconds(timeframe) <= lag_seconds <= maximum_lag


class MarketDataService:
    """Collect candle, tick, and spread data from MT5."""

    def __init__(self, log_level: str = "INFO", sleep_fn: Callable[[float], None] = time.sleep) -> None:
        self.logger = setup_logger(__name__, log_level)
        self.sleep_fn = sleep_fn

    def ensure_symbol(self, symbol: str) -> bool:
        normalized = normalize_symbol(symbol)
        info = mt5.symbol_info(normalized)
        if info is None:
            self.logger.error("Symbol not found in MT5: %s", normalized)
            return False

        if info.visible:
            return True

        if not mt5.symbol_select(normalized, True):
            self.logger.error("Failed to select symbol %s: %s", normalized, mt5.last_error())
            return False

        self.logger.info("Selected symbol in Market Watch: %s", normalized)
        return True

    def get_rates(self, symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
        normalized = normalize_symbol(symbol)
        if bars <= 0:
            self.logger.warning("Invalid bars value %s; returning empty DataFrame.", bars)
            return pd.DataFrame()

        if not self.ensure_symbol(normalized):
            return pd.DataFrame()

        try:
            mt5_timeframe = get_timeframe(timeframe)
        except ValueError as exc:
            self.logger.error(str(exc))
            return pd.DataFrame()

        rates = None
        tick = None
        for attempt in range(1, HISTORY_SYNC_ATTEMPTS + 1):
            rates = mt5.copy_rates_from_pos(normalized, mt5_timeframe, 0, bars)
            tick = mt5.symbol_info_tick(normalized)
            if rates_are_fresh(rates, tick, timeframe):
                break
            if attempt < HISTORY_SYNC_ATTEMPTS:
                if attempt == 1:
                    self.logger.warning(
                        "Waiting for current MT5 history for %s %s; cached candles are stale.",
                        normalized,
                        timeframe,
                    )
                self.sleep_fn(HISTORY_SYNC_DELAY_SECONDS)
        else:
            latest_rate_time = _value(rates[-1], "time") if rates is not None and len(rates) else None
            latest_tick_time = _value(tick, "time")
            self.logger.error(
                "Rejecting stale MT5 history for %s %s after %s attempts (rate_time=%s, tick_time=%s).",
                normalized,
                timeframe,
                HISTORY_SYNC_ATTEMPTS,
                latest_rate_time,
                latest_tick_time,
            )
            return pd.DataFrame()

        if rates is None:
            self.logger.warning("MT5 returned no rates for %s %s: %s", normalized, timeframe, mt5.last_error())
            return pd.DataFrame()
        if len(rates) == 0:
            self.logger.warning("MT5 returned an empty rates array for %s %s.", normalized, timeframe)
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        missing = [column for column in REQUIRED_RATE_COLUMNS if column not in df.columns]
        if missing:
            self.logger.error("Rates data missing required columns: %s", missing)
            return pd.DataFrame()

        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df["symbol"] = normalized
        df["requested_symbol"] = symbol
        df["broker_symbol"] = normalized
        df["timeframe"] = timeframe.strip().upper()
        df = df.sort_values("time").reset_index(drop=True)
        df["is_closed_candle"] = True
        if not df.empty:
            df.loc[df.index[-1], "is_closed_candle"] = False
        return df

    def get_multi_timeframe_rates(
        self,
        symbol: str,
        timeframes: list[str],
        bars: int,
    ) -> dict[str, pd.DataFrame]:
        data: dict[str, pd.DataFrame] = {}
        for timeframe in timeframes:
            timeframe_key = timeframe.strip().upper()
            df = self.get_rates(symbol, timeframe_key, bars)
            if df.empty:
                self.logger.warning("No data collected for %s %s.", symbol, timeframe_key)
                continue
            data[timeframe_key] = df
        return data

    def get_multi_symbol_rates(
        self,
        symbols: list[str],
        timeframes: list[str],
        bars: int,
    ) -> dict[str, dict[str, pd.DataFrame]]:
        data: dict[str, dict[str, pd.DataFrame]] = {}
        for symbol in symbols:
            broker_symbol = normalize_symbol(symbol)
            symbol_data = self.get_multi_timeframe_rates(broker_symbol, timeframes, bars)
            if not symbol_data:
                self.logger.warning("No data collected for symbol %s.", broker_symbol)
                continue
            data[broker_symbol] = symbol_data
        return data

    def get_latest_tick(self, symbol: str) -> dict[str, Any] | None:
        normalized = normalize_symbol(symbol)
        if not self.ensure_symbol(normalized):
            return None

        tick = mt5.symbol_info_tick(normalized)
        if tick is None:
            self.logger.warning("Latest tick unavailable for %s: %s", normalized, mt5.last_error())
            return None
        return tick._asdict()

    def get_spread_points(self, symbol: str) -> float | None:
        normalized = normalize_symbol(symbol)
        info = mt5.symbol_info(normalized)
        if info is None:
            self.logger.warning("Spread unavailable; symbol info missing for %s.", normalized)
            return None
        return float(info.spread)
