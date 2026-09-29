"""Stage 9.1 paper trade status and performance report."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import Settings
from mt5.connection import MT5Connection
from mt5.market_data import MarketDataService
from paper.paper_journal import PaperJournal
from paper.paper_monitor import build_paper_status_report, enrich_open_trades_with_market_data
from paper.paper_performance import append_performance_snapshot, calculate_paper_performance
from paper.paper_status_summary import build_paper_status_summary
from utils.logger import setup_logger


def main() -> int:
    settings = Settings.load()
    logger = setup_logger(__name__, settings.log_level)

    print("Advanced AI Scalping Bot - Stage 9.1 Paper Status")
    print("This script reviews paper trade status only. It does not place MT5 orders.")

    journal = PaperJournal(
        settings.paper_journal_path,
        settings.paper_events_path,
        settings.paper_open_trades_snapshot_path,
    )
    latest_states = journal.reconstruct_latest_trade_states()
    if not latest_states:
        print("No paper trades found. Run python scripts/check_paper_execution.py first.")
        return 1

    open_trades = journal.get_current_open_trades()
    closed_trades = journal.get_closed_trades()
    data = {}

    connection = MT5Connection(settings)
    if open_trades and not connection.initialize():
        message = "MT5 connection failed. Open trade floating metrics cannot be updated."
        logger.error(message)
        print(message)
        return 1

    try:
        if open_trades:
            symbols = sorted({trade.get("symbol") for trade in open_trades if trade.get("symbol")})
            timeframes = sorted({trade.get("timeframe") for trade in open_trades if trade.get("timeframe")})
            data = MarketDataService(settings.log_level).get_multi_symbol_rates(symbols, timeframes, settings.bars_per_timeframe)
        enriched_open = enrich_open_trades_with_market_data(open_trades, data)
        report = build_paper_status_report(enriched_open, closed_trades)
        performance = calculate_paper_performance(closed_trades)

        journal.save_status_report(report, settings.paper_status_report_path)
        journal.save_snapshot(enriched_open)
        journal.append_closed_trades_csv(closed_trades, settings.paper_closed_trades_path)
        append_performance_snapshot(performance, settings.paper_performance_report_path)

        print()
        print(build_paper_status_summary(report, performance))
        print()
        print(f"Paper status JSON: {settings.paper_status_report_path}")
        print(f"Closed trades CSV: {settings.paper_closed_trades_path}")
        print(f"Performance CSV: {settings.paper_performance_report_path}")
        logger.info("Stage 9.1 paper status check completed.")
        return 0
    except Exception as exc:
        logger.exception("Stage 9.1 paper status check failed safely: %s", exc)
        print(f"Paper status check failed safely: {exc}")
        return 1
    finally:
        if connection.is_connected():
            connection.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
