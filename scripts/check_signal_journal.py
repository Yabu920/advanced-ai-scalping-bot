"""Stage 5 signal journal diagnostics."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import Settings
from journal.decision_journal import DecisionJournal
from journal.journal_summary import build_journal_write_summary
from journal.signal_tracker import SignalTracker
from mt5.connection import MT5Connection
from mt5.market_data import MarketDataService
from scripts.check_signals import save_signal_json
from strategy.market_analyzer import MarketAnalyzer
from strategy.signal_engine import SignalEngine
from strategy.signal_summary import build_signal_summary
from utils.logger import setup_logger


def main() -> int:
    settings = Settings.load()
    logger = setup_logger(__name__, settings.log_level)

    print("Advanced AI Scalping Bot - Stage 5 Signal Journal")
    print("This script records signal decisions only. It does not place trades.")

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
        spread_map = {
            symbol: market_data.get_spread_points(symbol)
            for symbol in data
        }

        analysis = MarketAnalyzer().analyze_market(data, spread_map)
        signals = SignalEngine().generate_market_signals(data, analysis, settings)
        signal_json_path = save_signal_json(signals)

        csv_count = DecisionJournal(settings.decision_journal_path).append_signals(signals)
        jsonl_count = SignalTracker(settings.signal_history_path).append_signals(
            signals,
            track_watchlist=settings.track_watchlist_signals,
            track_rejected=settings.track_rejected_signals,
        )

        print()
        print(build_signal_summary(signals))
        print()
        print(f"Saved signal JSON: {signal_json_path}")
        print()
        print(
            build_journal_write_summary(
                csv_count,
                jsonl_count,
                settings.decision_journal_path,
                settings.signal_history_path,
            )
        )
        logger.info("Stage 5 signal journal check completed.")
        return 0 if signals else 1
    except Exception as exc:
        logger.exception("Stage 5 signal journal check failed safely: %s", exc)
        print(f"Signal journal check failed safely: {exc}")
        return 1
    finally:
        connection.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
