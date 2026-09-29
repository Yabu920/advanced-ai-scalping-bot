"""Stage 1 diagnostics runner for the Advanced AI Scalping Bot."""

from __future__ import annotations

from typing import Any

from config.settings import Settings
from mt5.connection import MT5Connection
from mt5.market_data import MarketDataService
from strategy.diagnostics import build_market_snapshot
from strategy.indicators import add_basic_indicators
from utils.logger import setup_logger


def format_value(value: Any, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def format_time(value: Any) -> str:
    if value is None:
        return "N/A"
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def print_account_summary(account_info: dict[str, Any] | None) -> None:
    if not account_info:
        print("Account: unavailable")
        return

    print(
        "Account: "
        f"login={account_info.get('login')}, "
        f"server={account_info.get('server')}, "
        f"balance={format_value(account_info.get('balance'))}, "
        f"equity={format_value(account_info.get('equity'))}, "
        f"currency={account_info.get('currency')}"
    )


def main() -> int:
    settings = Settings.load()
    logger = setup_logger(__name__, settings.log_level)

    print("Advanced AI Scalping Bot - Stage 1 Diagnostics")
    print("For multi-symbol data check, run: python scripts/check_market_data.py")
    logger.info("Starting Stage 1 diagnostics. No trading execution is enabled.")

    connection = MT5Connection(settings)
    if not connection.initialize():
        message = "MT5 connection failed. Open/login to MT5 or check .env settings."
        logger.error(message)
        print(message)
        return 1

    try:
        account_info = connection.get_account_info()
        print_account_summary(account_info)

        market_data = MarketDataService(settings.log_level)
        df = market_data.get_rates(
            settings.default_symbol,
            settings.default_timeframe,
            settings.default_bars,
        )
        if df.empty:
            message = "No market data available. Check symbol, timeframe, and MT5 connection."
            logger.error(message)
            print(message)
            return 1

        df = add_basic_indicators(df)
        snapshot = build_market_snapshot(df)
        if not snapshot.get("enough_data"):
            message = f"Market snapshot unavailable: {snapshot.get('reason', 'Unknown reason')}"
            logger.error(message)
            print(message)
            return 1

        spread_points = market_data.get_spread_points(settings.default_symbol)

        logger.info("Market snapshot: %s", snapshot)
        print(f"Symbol: {format_value(snapshot.get('symbol'))}")
        print(f"Timeframe: {format_value(snapshot.get('timeframe'))}")
        print(f"Latest candle: {format_time(snapshot.get('latest_time'))}")
        print(f"Close: {format_value(snapshot.get('latest_close'))}")
        print(f"EMA20: {format_value(snapshot.get('ema_20'))}")
        print(f"EMA50: {format_value(snapshot.get('ema_50'))}")
        print(f"EMA200: {format_value(snapshot.get('ema_200'))}")
        print(f"RSI14: {format_value(snapshot.get('rsi_14'))}")
        print(f"ATR14: {format_value(snapshot.get('atr_14'))}")
        print(f"Trend hint: {format_value(snapshot.get('trend_hint'))}")
        print(f"Spread points: {format_value(spread_points, digits=0)}")
        return 0
    except Exception as exc:
        logger.exception("Unexpected diagnostics error: %s", exc)
        print(f"Diagnostics failed safely: {exc}")
        return 1
    finally:
        connection.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
