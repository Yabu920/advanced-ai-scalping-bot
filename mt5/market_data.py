"""Market data collection from MetaTrader 5."""

from __future__ import annotations

from typing import Any

import MetaTrader5 as mt5
import pandas as pd

from config.symbols import normalize_symbol
from config.timeframes import get_timeframe
from utils.logger import setup_logger


REQUIRED_RATE_COLUMNS = ["time", "open", "high", "low", "close", "tick_volume", "spread"]


class MarketDataService:
    """Collect candle, tick, and spread data from MT5."""

    def __init__(self, log_level: str = "INFO") -> None:
        self.logger = setup_logger(__name__, log_level)

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

        rates = mt5.copy_rates_from_pos(normalized, mt5_timeframe, 0, bars)
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
