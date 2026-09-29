"""Stage 9 paper execution simulator."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import Settings
from mt5.connection import MT5Connection
from mt5.market_data import MarketDataService
from mt5.symbols import SymbolService
from paper.paper_engine import PaperExecutionEngine
from paper.paper_journal import PaperJournal
from paper.paper_summary import build_paper_summary
from paper.paper_trade import OPEN
from risk.pre_execution_summary import build_pre_execution_summary
from risk.pre_execution_validator import PreExecutionValidator
from risk.trade_plan import TradePlanBuilder
from risk.trade_plan_summary import build_trade_plan_summary
from strategy.market_analyzer import MarketAnalyzer
from strategy.signal_engine import SignalEngine
from strategy.signal_summary import build_signal_summary
from utils.logger import setup_logger


def main() -> int:
    settings = Settings.load()
    logger = setup_logger(__name__, settings.log_level)

    print("Advanced AI Scalping Bot - Stage 9 Paper Execution")
    print("This script simulates paper trades only. It does not place MT5 orders.")

    connection = MT5Connection(settings)
    if not connection.initialize():
        message = "MT5 connection failed. Run python scripts/check_mt5_connection.py for details."
        logger.error(message)
        print(message)
        return 1

    try:
        market_data = MarketDataService(settings.log_level)
        data = market_data.get_multi_symbol_rates(settings.symbols, settings.timeframes, settings.bars_per_timeframe)
        spread_map = {symbol: market_data.get_spread_points(symbol) for symbol in data}
        analysis = MarketAnalyzer().analyze_market(data, spread_map)
        signals = SignalEngine().generate_market_signals(data, analysis, settings)

        account_info = connection.get_account_info() or {}
        symbol_service = SymbolService()
        symbol_info_map = {symbol: symbol_service.get_symbol_info(symbol) or {"name": symbol} for symbol in data}
        plans = TradePlanBuilder(settings).build_plans_from_signals(signals, account_info, symbol_info_map)
        validations = PreExecutionValidator().validate_plans(plans, symbol_info_map, account_info, spread_map, settings)

        journal = PaperJournal(
            settings.paper_journal_path,
            settings.paper_events_path,
            settings.paper_open_trades_snapshot_path,
        )
        engine = PaperExecutionEngine(settings)
        existing_open = journal.load_open_trades()
        updated_existing = engine.update_open_trades(existing_open, data)
        still_open = [trade for trade in updated_existing if trade.get("status") == OPEN]
        new_trades = engine.create_paper_trades_from_plans(plans, validations, still_open)
        candidate_decisions = engine.last_candidate_decisions
        current_open = still_open + [trade for trade in new_trades if trade.get("status") == OPEN]

        journal.append_trades(new_trades)
        journal.append_trade_events([trade for trade in updated_existing if trade.get("status") == OPEN], "PAPER_TRADE_UPDATED")
        journal.append_trade_events([trade for trade in updated_existing if trade.get("status") != OPEN], "PAPER_TRADE_CLOSED")
        journal.save_snapshot(current_open)

        output = {
            "signals": signals,
            "plans": plans,
            "validations": validations,
            "new_trades": new_trades,
            "paper_candidate_decisions": candidate_decisions,
            "updated_trades": updated_existing,
            "open_trades": current_open,
        }
        journal.save_execution_output(output, settings.paper_execution_output_path)

        print()
        print(build_signal_summary(signals))
        print()
        print(build_trade_plan_summary(plans))
        print()
        print(build_pre_execution_summary(validations))
        print()
        print(build_paper_summary(new_trades, updated_existing, current_open))
        print()
        print("Filtered Paper Candidates:")
        for decision in candidate_decisions:
            state = "allowed" if decision["allowed"] else f"skipped: {decision['reason']}"
            print(f"- {decision['symbol']} {decision['timeframe']} {decision['direction']}: {state}")
        if current_open:
            print("Trade remains open because TP/SL has not been reached on the latest closed candle.")
        print()
        print(f"Saved paper execution JSON: {settings.paper_execution_output_path}")
        print("For detailed paper trade status, run: python scripts/check_paper_status.py")
        print("For continuous automatic paper testing, run:")
        print("python scripts/run_paper_bot.py")
        logger.info("Stage 9 paper execution completed.")
        return 0
    except Exception as exc:
        logger.exception("Stage 9 paper execution failed safely: %s", exc)
        print(f"Paper execution failed safely: {exc}")
        return 1
    finally:
        connection.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
