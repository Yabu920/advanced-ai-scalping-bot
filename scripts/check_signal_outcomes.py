"""Stage 6 signal outcome tracking diagnostics."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import Settings
from learning.outcome_summary import build_outcome_summary
from learning.outcome_tracker import OutcomeTracker
from mt5.connection import MT5Connection
from mt5.market_data import MarketDataService
from utils.logger import setup_logger


def _needed_symbols_and_timeframes(events: list[dict]) -> tuple[list[str], list[str]]:
    symbols = sorted({event.get("symbol") for event in events if event.get("symbol")})
    timeframes = sorted({event.get("timeframe") for event in events if event.get("timeframe")})
    return symbols, timeframes


def main() -> int:
    settings = Settings.load()
    logger = setup_logger(__name__, settings.log_level)

    print("Advanced AI Scalping Bot - Stage 6 Signal Outcomes")
    print("This script checks future outcomes of saved signal decisions. It does not place trades.")

    tracker = OutcomeTracker(settings.signal_history_path, settings.outcome_report_path)
    events = tracker.load_recent_signal_events(settings.outcome_max_events_to_check)
    if not events:
        print("No signal history found. Run python scripts/check_signal_journal.py first.")
        return 1

    symbols, timeframes = _needed_symbols_and_timeframes(events)
    bars = max(settings.bars_per_timeframe, settings.outcome_lookahead_candles + 100)

    connection = MT5Connection(settings)
    if not connection.initialize():
        message = "MT5 connection failed. Run python scripts/check_mt5_connection.py for details."
        logger.error(message)
        print(message)
        return 1

    try:
        market_data = MarketDataService(settings.log_level)
        data = market_data.get_multi_symbol_rates(symbols, timeframes, bars)
        results = tracker.evaluate_recent_events(data, settings)
        appended = tracker.append_outcome_report(results)

        print()
        print(build_outcome_summary(results))
        print()
        print(f"Outcome rows appended: {appended}")
        print(f"Outcome report path: {settings.outcome_report_path}")
        logger.info("Stage 6 signal outcome check completed. Appended %s rows.", appended)
        return 0
    except Exception as exc:
        logger.exception("Stage 6 signal outcome check failed safely: %s", exc)
        print(f"Signal outcome check failed safely: {exc}")
        return 1
    finally:
        connection.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
