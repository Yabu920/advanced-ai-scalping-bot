from types import SimpleNamespace

import pandas as pd

import paper.paper_bot_runner as runner_module
from paper.paper_bot_runner import PaperBotRunner
from paper.paper_journal import PaperJournal


def settings(tmp_path) -> SimpleNamespace:
    return SimpleNamespace(
        log_level="INFO",
        symbols=["GBPUSDm"],
        timeframes=["M5"],
        bars_per_timeframe=10,
        paper_bot_primary_timeframe="M5",
        paper_bot_run_on_new_candle_only=True,
        paper_bot_heartbeat_path=str(tmp_path / "heartbeat.json"),
        paper_bot_run_log_path=str(tmp_path / "run.log"),
        paper_bot_analysis_report_path=str(tmp_path / "analysis.json"),
        paper_bot_analysis_markdown_path=str(tmp_path / "analysis.md"),
        paper_bot_poll_seconds=1,
        paper_bot_stop_after_closed_trades=1,
        paper_bot_max_cycles=0,
        paper_bot_status_every_cycles=1,
        paper_bot_loop_enabled=True,
        paper_filters_enabled=False,
        paper_allowed_symbols=[],
        paper_allowed_timeframes=[],
        paper_allowed_directions=[],
        paper_min_signal_score=0.0,
        paper_allowed_signal_statuses=["WATCHLIST", "ELIGIBLE"],
        paper_require_costs_valid=True,
        paper_require_broker_constraints_valid=True,
        paper_experiment_name="baseline",
        paper_journal_path=str(tmp_path / "paper.csv"),
        paper_events_path=str(tmp_path / "paper.jsonl"),
        paper_open_trades_snapshot_path=str(tmp_path / "open.json"),
        paper_execution_output_path=str(tmp_path / "execution.json"),
        paper_status_report_path=str(tmp_path / "status.json"),
        paper_closed_trades_path=str(tmp_path / "closed.csv"),
        paper_performance_report_path=str(tmp_path / "performance.csv"),
        paper_trading_enabled=True,
        paper_trade_eligible_only=False,
        paper_include_watchlist=True,
        paper_max_open_trades=5,
        paper_max_open_trades_per_symbol=1,
        paper_use_pre_execution_validation=True,
        allow_watchlist_plan_preview=True,
        require_eligible_signal_for_execution=True,
        check_margin_requirement=False,
        risk_per_trade_percent=0.5,
        use_fixed_risk_amount=True,
        fixed_risk_amount=5.0,
        default_rr_ratio=2.0,
        min_rr_ratio=1.5,
        atr_sl_multiplier=1.2,
        min_stop_atr_multiplier=0.8,
        max_stop_atr_multiplier=3.0,
    )


def market_df(time: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "time": pd.Timestamp(time),
                "open": 1.0,
                "high": 1.1,
                "low": 0.9,
                "close": 1.0,
                "is_closed_candle": True,
            }
        ]
    )


class FakeMarketData:
    def __init__(self, time: str) -> None:
        self.time = time

    def get_multi_symbol_rates(self, symbols, timeframes, bars):
        return {"GBPUSDm": {"M5": market_df(self.time)}}

    def get_spread_points(self, symbol):
        return 10.0


class FakeConnection:
    def initialize(self):
        return True

    def shutdown(self):
        return None

    def get_account_info(self):
        return {"equity": 1000.0, "balance": 1000.0}


class FakeSymbolService:
    def get_symbol_info(self, symbol):
        return {"name": symbol, "trade_tick_size": 0.00001, "trade_tick_value": 1.0, "volume_min": 0.01, "volume_max": 100, "volume_step": 0.01}


class FakeMarketAnalyzer:
    def analyze_market(self, data, spread_map):
        return {"GBPUSDm": {"multi_timeframe_bias": {"bias": "bullish", "confidence": 70}, "timeframes": {}}}


class FakeSignalEngine:
    def generate_market_signals(self, data, analysis, settings):
        return {"GBPUSDm": {"signals": {"M5": {"symbol": "GBPUSDm", "timeframe": "M5", "direction": "BUY", "status": "WATCHLIST", "score": 60}}}}


class FakeTradePlanBuilder:
    def __init__(self, settings):
        pass

    def build_plans_from_signals(self, signals, account_info, symbol_info_map):
        return {
            "GBPUSDm": {
                "M5": {
                    "symbol": "GBPUSDm",
                    "timeframe": "M5",
                    "direction": "BUY",
                    "signal_status": "WATCHLIST",
                    "signal_score": 60,
                    "valid": True,
                    "entry_reference": 1.0,
                    "stop_loss": 0.99,
                    "take_profit": 1.02,
                    "risk_amount": 5.0,
                    "risk_percent": 0.5,
                    "lot_size": 0.01,
                    "rr_ratio": 2.0,
                    "signal_candle_time": "2026-06-17T10:00:00+00:00",
                    "opened_candle_time": "2026-06-17T10:00:00+00:00",
                    "latest_time": "2026-06-17T10:00:00+00:00",
                    "issues": [],
                }
            }
        }


class FakeValidator:
    def validate_plans(self, plans, symbol_info_map, account_info, spread_map, settings):
        return {"GBPUSDm": {"M5": {"plan_valid": True, "broker_constraints_valid": True, "costs_valid": True, "execution_ready_later": False}}}


def patch_pipeline(monkeypatch) -> None:
    monkeypatch.setattr(runner_module, "MarketAnalyzer", FakeMarketAnalyzer)
    monkeypatch.setattr(runner_module, "SignalEngine", FakeSignalEngine)
    monkeypatch.setattr(runner_module, "TradePlanBuilder", FakeTradePlanBuilder)
    monkeypatch.setattr(runner_module, "PreExecutionValidator", lambda: FakeValidator())


def make_runner(tmp_path, candle_time: str = "2026-06-17T10:00:00+00:00") -> PaperBotRunner:
    s = settings(tmp_path)
    return PaperBotRunner(
        s,
        connection=FakeConnection(),
        market_data=FakeMarketData(candle_time),
        symbol_service=FakeSymbolService(),
        journal=PaperJournal(s.paper_journal_path, s.paper_events_path, s.paper_open_trades_snapshot_path),
        sleep_fn=lambda seconds: None,
    )


def test_runner_skips_cycle_when_no_new_candle_and_enabled(tmp_path) -> None:
    runner = make_runner(tmp_path)
    runner.last_closed_candle_times[("GBPUSDm", "M5")] = pd.Timestamp("2026-06-17T10:00:00Z")
    result = runner.run_cycle(1)
    assert result["skipped"] is True


def test_runner_processes_cycle_when_new_candle_appears(tmp_path, monkeypatch) -> None:
    patch_pipeline(monkeypatch)
    runner = make_runner(tmp_path)
    result = runner.run_cycle(1)
    assert result["skipped"] is False
    assert len(result["new_trades"]) == 1


def test_delayed_symbol_candle_is_processed_even_if_other_symbol_is_ahead(tmp_path, monkeypatch) -> None:
    patch_pipeline(monkeypatch)
    runner = make_runner(tmp_path)
    runner.market_data.get_multi_symbol_rates = lambda *args: {
        "GBPUSDm": {"M5": market_df("2026-06-17T10:05:00Z")},
        "EURUSDm": {"M5": market_df("2026-06-17T10:00:00Z")},
    }
    runner.last_closed_candle_times[("GBPUSDm", "M5")] = pd.Timestamp("2026-06-17T10:05:00Z")

    result = runner.run_cycle(1)

    assert result["skipped"] is False
    assert result["new_trades"] == []  # The unchanged GBP plan must not be reopened.
    assert runner.last_closed_candle_times[("EURUSDm", "M5")] == pd.Timestamp("2026-06-17T10:00:00Z")


def test_m1_candle_triggers_cycle_when_m5_is_unchanged(tmp_path, monkeypatch) -> None:
    patch_pipeline(monkeypatch)
    runner = make_runner(tmp_path)
    runner.settings.signal_timeframes = ["M1", "M5"]
    runner.market_data.get_multi_symbol_rates = lambda *args: {
        "GBPUSDm": {
            "M1": market_df("2026-06-17T10:01:00Z"),
            "M5": market_df("2026-06-17T10:00:00Z"),
        }
    }
    runner.last_closed_candle_times[("GBPUSDm", "M1")] = pd.Timestamp("2026-06-17T10:00:00Z")
    runner.last_closed_candle_times[("GBPUSDm", "M5")] = pd.Timestamp("2026-06-17T10:00:00Z")

    result = runner.run_cycle(1)

    assert result["skipped"] is False
    assert result["new_trades"] == []  # M5 has no new signal candle.
    assert runner.last_closed_candle_times[("GBPUSDm", "M1")] == pd.Timestamp("2026-06-17T10:01:00Z")


def test_older_closed_candle_never_moves_market_watermark_backwards(tmp_path) -> None:
    runner = make_runner(tmp_path, candle_time="2026-06-17T10:00:00Z")
    runner.last_closed_candle_times[("GBPUSDm", "M5")] = pd.Timestamp("2026-06-17T10:05:00Z")
    result = runner.run_cycle(1)
    assert result["skipped"] is True
    assert runner.last_closed_candle_times[("GBPUSDm", "M5")] == pd.Timestamp("2026-06-17T10:05:00Z")


def test_runner_stops_after_configured_closed_trade_target(tmp_path) -> None:
    runner = make_runner(tmp_path)
    runner.journal.append_trade_events([{"paper_trade_id": "1", "status": "CLOSED_TP"}], "PAPER_TRADE_CLOSED")
    assert runner.should_stop_for_closed_target(1) is True


def test_duplicate_same_candle_signal_is_not_reopened(tmp_path) -> None:
    runner = make_runner(tmp_path)
    existing_trade = {
        "paper_trade_id": "1",
        "symbol": "GBPUSDm",
        "timeframe": "M5",
        "direction": "BUY",
        "signal_candle_time": "2026-06-17T10:00:00+00:00",
        "status": "CLOSED_TP",
    }
    runner.journal.append_trade_events([existing_trade], "PAPER_TRADE_CLOSED")
    plans = FakeTradePlanBuilder(settings(tmp_path)).build_plans_from_signals({}, {}, {})
    filtered = runner.filter_duplicate_same_candle_plans(plans, [])
    assert filtered["GBPUSDm"]["M5"]["valid"] is False
    assert "Duplicate same-candle paper signal already exists." in filtered["GBPUSDm"]["M5"]["issues"]
