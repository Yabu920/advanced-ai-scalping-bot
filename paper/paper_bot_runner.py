"""Continuous paper trading runner for Stage 10."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from mt5.connection import MT5Connection
from mt5.market_data import MarketDataService
from mt5.symbols import SymbolService
from paper.paper_analysis import analyze_closed_paper_trades
from paper.paper_analysis_summary import build_paper_analysis_markdown
from paper.paper_engine import PaperExecutionEngine
from paper.paper_filters import paper_filter_summary
from paper.paper_journal import PaperJournal, to_json_safe
from paper.paper_monitor import (
    build_paper_status_report,
    enrich_open_trades_with_market_data,
)
from paper.paper_performance import (
    append_performance_snapshot,
    calculate_paper_performance,
)
from paper.paper_trade import OPEN
from risk.pre_execution_validator import PreExecutionValidator
from risk.trade_plan import TradePlanBuilder
from strategy.market_analyzer import MarketAnalyzer
from strategy.signal_engine import SignalEngine


class PaperBotRunner:
    """Run the paper execution workflow continuously without broker orders."""

    def __init__(
        self,
        settings: Any,
        connection: Any | None = None,
        market_data: Any | None = None,
        symbol_service: Any | None = None,
        journal: PaperJournal | None = None,
        sleep_fn: Callable[[int], None] = time.sleep,
        logger: Any | None = None,
    ) -> None:
        self.settings = settings
        self.connection = connection or MT5Connection(settings)
        self.market_data = market_data or MarketDataService(settings.log_level)
        self.symbol_service = symbol_service or SymbolService()
        self.journal = journal or PaperJournal(
            settings.paper_journal_path,
            settings.paper_events_path,
            settings.paper_open_trades_snapshot_path,
        )
        self.sleep_fn = sleep_fn
        self.logger = logger
        self.last_closed_candle_times: dict[tuple[str, str], pd.Timestamp] = {}

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _to_iso(value: Any) -> str | None:
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            return value.isoformat()
        text = str(value).strip()
        return text or None

    def _write_json(self, path: str, payload: dict[str, Any]) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(to_json_safe(payload), indent=2), encoding="utf-8")

    def _write_text(self, path: str, text: str) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")

    def _append_run_log(self, message: str) -> None:
        path = Path(self.settings.paper_bot_run_log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(f"{self._utc_now()} | {message}\n")

    @staticmethod
    def _closed_time(df: pd.DataFrame | None) -> pd.Timestamp | None:
        if df is None or df.empty or "time" not in df.columns:
            return None
        if "is_closed_candle" in df.columns:
            closed = df[df["is_closed_candle"] == True]
        else:
            closed = df.iloc[:-1]
        if closed.empty:
            return None
        times = pd.to_datetime(closed["time"], errors="coerce", utc=True).dropna()
        return times.max() if not times.empty else None

    def signal_candle_times(self, data: dict[str, dict[str, pd.DataFrame]]) -> dict[tuple[str, str], pd.Timestamp]:
        signal_timeframes = getattr(self.settings, "signal_timeframes", self.settings.timeframes)
        times: dict[tuple[str, str], pd.Timestamp] = {}
        for symbol, symbol_data in data.items():
            for timeframe in signal_timeframes:
                timestamp = self._closed_time(symbol_data.get(timeframe))
                if timestamp is not None:
                    times[(symbol, timeframe)] = timestamp
        return times

    def latest_closed_candle_time(self, data: dict[str, dict[str, pd.DataFrame]]) -> str | None:
        timeframe = self.settings.paper_bot_primary_timeframe
        times = [
            timestamp
            for symbol_data in data.values()
            if (timestamp := self._closed_time(symbol_data.get(timeframe))) is not None
        ]
        return max(times).isoformat() if times else None

    def closed_trade_count(self) -> int:
        return len(self.journal.get_closed_trades())

    def should_stop_for_closed_target(self, stop_after_closed_trades: int | None = None) -> bool:
        target = stop_after_closed_trades if stop_after_closed_trades is not None else self.settings.paper_bot_stop_after_closed_trades
        return target > 0 and self.closed_trade_count() >= target

    def duplicate_signal_keys(self) -> set[tuple[str, str, str, str]]:
        keys: set[tuple[str, str, str, str]] = set()
        for event in self.journal.load_all_trade_events():
            trade = event.get("paper_trade", {})
            symbol = trade.get("symbol")
            timeframe = trade.get("timeframe")
            direction = trade.get("direction")
            signal_time = trade.get("signal_candle_time") or trade.get("opened_candle_time")
            if symbol and timeframe and direction and signal_time:
                keys.add((str(symbol), str(timeframe), str(direction), str(signal_time)))
        return keys

    def filter_duplicate_same_candle_plans(self, plans: dict[str, Any], existing_open: list[dict]) -> dict[str, Any]:
        duplicate_keys = self.duplicate_signal_keys()
        for trade in existing_open:
            signal_time = trade.get("signal_candle_time") or trade.get("opened_candle_time")
            if trade.get("symbol") and trade.get("timeframe") and trade.get("direction") and signal_time:
                duplicate_keys.add((str(trade["symbol"]), str(trade["timeframe"]), str(trade["direction"]), str(signal_time)))

        filtered: dict[str, Any] = {}
        for symbol, symbol_plans in plans.items():
            filtered[symbol] = {}
            for timeframe, plan in symbol_plans.items():
                signal_time = plan.get("signal_candle_time") or plan.get("opened_candle_time") or plan.get("latest_time")
                key = (str(symbol), str(timeframe), str(plan.get("direction")), str(signal_time))
                if signal_time and key in duplicate_keys:
                    duplicate_plan = dict(plan)
                    duplicate_plan["valid"] = False
                    duplicate_plan["executable_later"] = False
                    duplicate_plan["issues"] = list(duplicate_plan.get("issues", [])) + ["Duplicate same-candle paper signal already exists."]
                    filtered[symbol][timeframe] = duplicate_plan
                else:
                    filtered[symbol][timeframe] = plan
        return filtered

    def _save_analysis(self, closed_trades: list[dict]) -> dict[str, Any]:
        analysis = analyze_closed_paper_trades(closed_trades)
        markdown = build_paper_analysis_markdown(analysis)
        self._write_json(self.settings.paper_bot_analysis_report_path, analysis)
        self._write_text(self.settings.paper_bot_analysis_markdown_path, markdown)
        return analysis

    def run_cycle(self, cycle_number: int) -> dict[str, Any]:
        data = self.market_data.get_multi_symbol_rates(
            self.settings.symbols,
            self.settings.timeframes,
            self.settings.bars_per_timeframe,
        )
        latest_candle_time = self.latest_closed_candle_time(data)
        candle_times = self.signal_candle_times(data)
        changed_keys = {
            key
            for key, timestamp in candle_times.items()
            if key not in self.last_closed_candle_times or timestamp > self.last_closed_candle_times[key]
        }
        skipped = self.settings.paper_bot_run_on_new_candle_only and not changed_keys
        heartbeat = {
            "heartbeat_time_utc": self._utc_now(),
            "cycle": cycle_number,
            "latest_closed_candle_time": latest_candle_time,
            "new_signal_candles": [f"{symbol}/{timeframe}" for symbol, timeframe in sorted(changed_keys)],
            "skipped": skipped,
            "reason": "No new closed candle." if skipped else "Processed cycle.",
        }

        if skipped:
            self._write_json(self.settings.paper_bot_heartbeat_path, heartbeat)
            self._append_run_log(f"Cycle {cycle_number}: skipped; no new closed candle.")
            return {
                "cycle": cycle_number,
                "skipped": True,
                "latest_closed_candle_time": latest_candle_time,
                "new_trades": [],
                "updated_trades": [],
                "open_trades": self.journal.get_current_open_trades(),
                "closed_trades": self.journal.get_closed_trades(),
            }

        spread_map = {symbol: self.market_data.get_spread_points(symbol) for symbol in data}
        analysis = MarketAnalyzer().analyze_market(data, spread_map)
        signals = SignalEngine().generate_market_signals(data, analysis, self.settings)
        account_info = self.connection.get_account_info() or {}
        symbol_info_map = {symbol: self.symbol_service.get_symbol_info(symbol) or {"name": symbol} for symbol in data}
        plans = TradePlanBuilder(self.settings).build_plans_from_signals(signals, account_info, symbol_info_map)
        existing_open = self.journal.load_open_trades()
        plans = self.filter_duplicate_same_candle_plans(plans, existing_open)
        if self.settings.paper_bot_run_on_new_candle_only:
            plans = {
                symbol: {
                    timeframe: plan
                    for timeframe, plan in symbol_plans.items()
                    if (symbol, timeframe) in changed_keys
                }
                for symbol, symbol_plans in plans.items()
            }
        validations = PreExecutionValidator().validate_plans(plans, symbol_info_map, account_info, spread_map, self.settings)

        engine = PaperExecutionEngine(self.settings)
        updated_existing = engine.update_open_trades(existing_open, data)
        still_open = [trade for trade in updated_existing if trade.get("status") == OPEN]
        new_trades = engine.create_paper_trades_from_plans(plans, validations, still_open, symbol_info_map)
        candidate_decisions = engine.last_candidate_decisions
        current_open = still_open + [trade for trade in new_trades if trade.get("status") == OPEN]

        self.journal.append_trades(new_trades)
        self.journal.append_trade_events([trade for trade in updated_existing if trade.get("status") == OPEN], "PAPER_TRADE_UPDATED")
        self.journal.append_trade_events([trade for trade in updated_existing if trade.get("status") != OPEN], "PAPER_TRADE_CLOSED")
        self.journal.save_snapshot(current_open)

        closed_trades = self.journal.get_closed_trades()
        enriched_open = enrich_open_trades_with_market_data(current_open, data)
        status_report = build_paper_status_report(enriched_open, closed_trades)
        performance = calculate_paper_performance(closed_trades)
        self.journal.save_status_report(status_report, self.settings.paper_status_report_path)
        self.journal.append_closed_trades_csv(closed_trades, self.settings.paper_closed_trades_path)
        append_performance_snapshot(performance, self.settings.paper_performance_report_path)
        clean_analysis = self._save_analysis(closed_trades)

        output = {
            "cycle": cycle_number,
            "signals": signals,
            "plans": plans,
            "validations": validations,
            "new_trades": new_trades,
            "paper_candidate_decisions": candidate_decisions,
            "updated_trades": updated_existing,
            "open_trades": current_open,
            "status_report": status_report,
            "performance": performance,
            "analysis": clean_analysis,
        }
        self.journal.save_execution_output(output, self.settings.paper_execution_output_path)

        heartbeat.update(
            {
                "new_trades_opened": len(new_trades),
                "trades_closed_this_cycle": len([trade for trade in updated_existing if trade.get("status") != OPEN]),
                "open_trades": len(current_open),
                "closed_trades_total": len(closed_trades),
                "total_r": performance.get("total_r", 0.0),
                "total_pnl": performance.get("total_pnl", 0.0),
            }
        )
        self._write_json(self.settings.paper_bot_heartbeat_path, heartbeat)
        self._append_run_log(
            f"Cycle {cycle_number}: new={len(new_trades)} closed={heartbeat['trades_closed_this_cycle']} "
            f"open={len(current_open)} total_closed={len(closed_trades)} filtered="
            f"{len([item for item in candidate_decisions if item['filtered_by_paper_filters']])}"
        )
        self.last_closed_candle_times.update(
            {key: candle_times[key] for key in changed_keys}
        )
        return {
            "cycle": cycle_number,
            "skipped": False,
            "latest_closed_candle_time": latest_candle_time,
            "new_trades": new_trades,
            "paper_candidate_decisions": candidate_decisions,
            "updated_trades": updated_existing,
            "open_trades": current_open,
            "closed_trades": closed_trades,
            "performance": performance,
        }

    def format_cycle_summary(self, result: dict[str, Any]) -> str:
        performance = result.get("performance", {})
        closed_total = len(result.get("closed_trades", []))
        target = self.settings.paper_bot_stop_after_closed_trades
        return "\n".join(
            [
                f"# Paper Bot Cycle {result.get('cycle')}",
                "",
                f"Latest {self.settings.paper_bot_primary_timeframe} closed candle: {result.get('latest_closed_candle_time')}",
                f"New trades opened: {len(result.get('new_trades', []))}",
                f"Trades closed: {len([trade for trade in result.get('updated_trades', []) if trade.get('status') != OPEN])}",
                f"Open trades: {len(result.get('open_trades', []))}",
                f"Closed trades total: {closed_total} / {target}",
                f"Current result: {performance.get('total_r', 0.0):+.1f}R | ${performance.get('total_pnl', 0.0):+.2f}",
                f"Cost coverage: {performance.get('complete_cost_trades', 0)} complete / {performance.get('incomplete_cost_trades', 0)} incomplete; modeled paper result only",
                f"Next check in {self.settings.paper_bot_poll_seconds} seconds",
            ]
        )

    def run(self, max_cycles: int | None = None, stop_after_closed_trades: int | None = None) -> int:
        if not self.settings.paper_bot_loop_enabled:
            print("Paper bot loop is disabled by PAPER_BOT_LOOP_ENABLED.")
            return 0
        max_cycles_value = self.settings.paper_bot_max_cycles if max_cycles is None else max_cycles
        cycle = 0
        self._append_run_log(f"Startup paper filters: {paper_filter_summary(self.settings)}")
        if not self.connection.initialize():
            print("MT5 connection failed. Run python scripts/check_mt5_connection.py for details.")
            return 1
        try:
            while True:
                if self.should_stop_for_closed_target(stop_after_closed_trades):
                    print("Paper bot closed-trade target reached. Stopping.")
                    return 0
                if max_cycles_value and cycle >= max_cycles_value:
                    print("Paper bot max cycle limit reached. Stopping.")
                    return 0

                cycle += 1
                result = self.run_cycle(cycle)
                if result.get("skipped"):
                    print(f"Paper Bot Cycle {cycle}: no new closed candle. Heartbeat saved.")
                elif cycle % self.settings.paper_bot_status_every_cycles == 0:
                    print(self.format_cycle_summary(result))

                if self.should_stop_for_closed_target(stop_after_closed_trades):
                    print("Paper bot closed-trade target reached. Stopping.")
                    return 0
                if max_cycles_value and cycle >= max_cycles_value:
                    print("Paper bot max cycle limit reached. Stopping.")
                    return 0
                self.sleep_fn(self.settings.paper_bot_poll_seconds)
        except KeyboardInterrupt:
            print("Paper bot stopped by user.")
            return 0
        finally:
            self.connection.shutdown()
