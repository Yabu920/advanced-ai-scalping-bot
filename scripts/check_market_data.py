"""Stage 2 multi-symbol, multi-timeframe market data check."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import Settings
from mt5.connection import MT5Connection
from mt5.market_data import MarketDataService
from strategy.data_summary import build_data_collection_summary
from strategy.data_validation import validate_multi_symbol_data
from utils.logger import setup_logger


def save_live_csv_files(data: dict) -> None:
    output_dir = PROJECT_ROOT / "data" / "live"
    output_dir.mkdir(parents=True, exist_ok=True)

    for symbol, timeframe_data in data.items():
        for timeframe, df in timeframe_data.items():
            if df.empty:
                continue
            output_path = output_dir / f"{symbol}_{timeframe}_latest.csv"
            df.to_csv(output_path, index=False)


def main() -> int:
    settings = Settings.load()
    logger = setup_logger(__name__, settings.log_level)

    print("Advanced AI Scalping Bot - Stage 2 Market Data Check")
    print("This script collects market data only. It does not place trades.")
    print(f"Symbols: {', '.join(settings.symbols)}")
    print(f"Timeframes: {', '.join(settings.timeframes)}")
    print(f"Bars per timeframe: {settings.bars_per_timeframe}")

    connection = MT5Connection(settings)
    if not connection.initialize():
        message = "MT5 connection failed. Run python scripts/check_mt5_connection.py for details."
        logger.error(message)
        print(message)
        return 1

    try:
        market_data = MarketDataService(settings.log_level)
        data = market_data.get_multi_symbol_rates(
            settings.symbols,
            settings.timeframes,
            settings.bars_per_timeframe,
        )
        validation = validate_multi_symbol_data(data)
        summary = build_data_collection_summary(data, validation)

        save_live_csv_files(data)
        logger.info("Stage 2 market data check completed.")
        print()
        print(summary)
        return 0 if data else 1
    except Exception as exc:
        logger.exception("Stage 2 market data check failed safely: %s", exc)
        print(f"Market data check failed safely: {exc}")
        return 1
    finally:
        connection.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
