"""Application settings loaded from environment variables."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from config.symbols import normalize_symbol


def _empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _safe_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _parse_csv_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_symbols(value: str | None, fallback: str) -> list[str]:
    symbols = [normalize_symbol(symbol) for symbol in _parse_csv_list(value)]
    return symbols or [normalize_symbol(fallback)]


def _parse_timeframes(value: str | None, fallback: str) -> list[str]:
    timeframes = [timeframe.strip().upper() for timeframe in _parse_csv_list(value)]
    fallback_timeframes = [timeframe.strip().upper() for timeframe in _parse_csv_list(fallback)]
    return timeframes or fallback_timeframes or [fallback.strip().upper()]


def _safe_score(value: str | None, default: int) -> int:
    score = _safe_int(value, default)
    return score if 1 <= score <= 100 else default


def _safe_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    return default


def _safe_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _optional_nonnegative_float(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) and parsed >= 0 else None


def _safe_bounded_int(value: str | None, default: int, minimum: int, maximum: int | None = None) -> int:
    parsed = _safe_int(value, default)
    if parsed < minimum:
        return default
    if maximum is not None and parsed > maximum:
        return default
    return parsed


@dataclass(frozen=True)
class Settings:
    mt5_login: int | None
    mt5_password: str | None
    mt5_server: str | None
    mt5_path: str | None
    default_symbol: str
    default_timeframe: str
    default_bars: int
    symbols: list[str]
    timeframes: list[str]
    bars_per_timeframe: int
    signal_timeframes: list[str]
    bias_timeframes: list[str]
    min_signal_score: int
    watchlist_score: int
    allow_mixed_bias: bool
    decision_journal_path: str
    signal_history_path: str
    track_watchlist_signals: bool
    track_rejected_signals: bool
    outcome_lookahead_candles: int
    outcome_min_move_atr: float
    outcome_adverse_move_atr: float
    outcome_max_events_to_check: int
    outcome_report_path: str
    risk_per_trade_percent: float
    max_risk_per_trade_percent: float
    default_rr_ratio: float
    min_rr_ratio: float
    atr_sl_multiplier: float
    atr_tp_multiplier: float
    use_fixed_risk_amount: bool
    fixed_risk_amount: float
    min_stop_atr_multiplier: float
    max_stop_atr_multiplier: float
    max_spread_to_atr_ratio: float
    max_spread_cost_risk_percent: float
    max_spread_to_sl_ratio: float
    max_spread_to_tp_ratio: float
    min_net_rr_after_spread: float
    min_stop_distance_points: float
    min_tp_distance_points: float
    require_eligible_signal_for_execution: bool
    allow_watchlist_plan_preview: bool
    check_margin_requirement: bool
    paper_trading_enabled: bool
    paper_trade_eligible_only: bool
    paper_include_watchlist: bool
    paper_journal_path: str
    paper_events_path: str
    paper_open_trades_snapshot_path: str
    paper_execution_output_path: str
    paper_closed_trades_path: str
    paper_status_report_path: str
    paper_performance_report_path: str
    paper_max_open_trades: int
    paper_max_open_trades_per_symbol: int
    paper_use_pre_execution_validation: bool
    paper_commission_per_lot_round_trip: float | None
    paper_slippage_points_per_side: float | None
    paper_bot_loop_enabled: bool
    paper_bot_poll_seconds: int
    paper_bot_primary_timeframe: str
    paper_bot_run_on_new_candle_only: bool
    paper_bot_max_cycles: int
    paper_bot_stop_after_closed_trades: int
    paper_bot_status_every_cycles: int
    paper_bot_heartbeat_path: str
    paper_bot_run_log_path: str
    paper_bot_analysis_report_path: str
    paper_bot_analysis_markdown_path: str
    paper_filters_enabled: bool
    paper_allowed_symbols: list[str]
    paper_allowed_timeframes: list[str]
    paper_allowed_directions: list[str]
    paper_min_signal_score: float
    paper_allowed_signal_statuses: list[str]
    paper_require_costs_valid: bool
    paper_require_broker_constraints_valid: bool
    paper_experiment_name: str
    log_level: str

    @classmethod
    def load(cls) -> Settings:
        # Resolve the project environment independently of the caller's working
        # directory. This keeps every entry script on the same configuration.
        env_path = Path(__file__).resolve().parents[1] / ".env"
        load_dotenv(dotenv_path=env_path)

        login_value = _empty_to_none(os.getenv("MT5_LOGIN"))
        login = _safe_int(login_value, 0) if login_value else None
        default_symbol = os.getenv("DEFAULT_SYMBOL", "XAUUSD").strip() or "XAUUSD"
        default_timeframe = os.getenv("DEFAULT_TIMEFRAME", "M5").strip().upper() or "M5"
        default_bars = _safe_int(os.getenv("DEFAULT_BARS"), 300)
        min_signal_score = _safe_score(os.getenv("MIN_SIGNAL_SCORE"), 70)
        watchlist_score = _safe_score(os.getenv("WATCHLIST_SCORE"), 55)
        if watchlist_score >= min_signal_score:
            watchlist_score = 55
        max_risk_percent = min(_safe_float(os.getenv("MAX_RISK_PER_TRADE_PERCENT"), 1.0), 5.0)
        risk_percent = _safe_float(os.getenv("RISK_PER_TRADE_PERCENT"), 0.5)
        if risk_percent > max_risk_percent:
            risk_percent = min(0.5, max_risk_percent)
        min_rr_ratio = _safe_float(os.getenv("MIN_RR_RATIO"), 1.5)
        default_rr_ratio = _safe_float(os.getenv("DEFAULT_RR_RATIO"), 2.0)
        default_rr_ratio = max(default_rr_ratio, min_rr_ratio)
        min_stop_multiplier = _safe_float(os.getenv("MIN_STOP_ATR_MULTIPLIER"), 0.8)
        max_stop_multiplier = _safe_float(os.getenv("MAX_STOP_ATR_MULTIPLIER"), 3.0)
        max_stop_multiplier = max(max_stop_multiplier, min_stop_multiplier)

        return cls(
            mt5_login=login,
            mt5_password=_empty_to_none(os.getenv("MT5_PASSWORD")),
            mt5_server=_empty_to_none(os.getenv("MT5_SERVER")),
            mt5_path=_empty_to_none(os.getenv("MT5_PATH")),
            default_symbol=default_symbol,
            default_timeframe=default_timeframe,
            default_bars=default_bars,
            symbols=_parse_symbols(os.getenv("SYMBOLS"), default_symbol),
            timeframes=_parse_timeframes(os.getenv("TIMEFRAMES"), default_timeframe),
            bars_per_timeframe=_safe_int(os.getenv("BARS_PER_TIMEFRAME"), default_bars or 500),
            signal_timeframes=_parse_timeframes(os.getenv("SIGNAL_TIMEFRAMES"), "M1,M5"),
            bias_timeframes=_parse_timeframes(os.getenv("BIAS_TIMEFRAMES"), "M15,H1"),
            min_signal_score=min_signal_score,
            watchlist_score=watchlist_score,
            allow_mixed_bias=_safe_bool(os.getenv("ALLOW_MIXED_BIAS"), False),
            decision_journal_path=os.getenv("DECISION_JOURNAL_PATH", "data/logs/decision_journal.csv").strip()
            or "data/logs/decision_journal.csv",
            signal_history_path=os.getenv("SIGNAL_HISTORY_PATH", "data/logs/signal_history.jsonl").strip()
            or "data/logs/signal_history.jsonl",
            track_watchlist_signals=_safe_bool(os.getenv("TRACK_WATCHLIST_SIGNALS"), True),
            track_rejected_signals=_safe_bool(os.getenv("TRACK_REJECTED_SIGNALS"), True),
            outcome_lookahead_candles=_safe_bounded_int(os.getenv("OUTCOME_LOOKAHEAD_CANDLES"), 12, 1, 200),
            outcome_min_move_atr=_safe_float(os.getenv("OUTCOME_MIN_MOVE_ATR"), 1.0),
            outcome_adverse_move_atr=_safe_float(os.getenv("OUTCOME_ADVERSE_MOVE_ATR"), 0.7),
            outcome_max_events_to_check=_safe_bounded_int(os.getenv("OUTCOME_MAX_EVENTS_TO_CHECK"), 200, 1),
            outcome_report_path=os.getenv("OUTCOME_REPORT_PATH", "data/logs/signal_outcome_report.csv").strip()
            or "data/logs/signal_outcome_report.csv",
            risk_per_trade_percent=risk_percent,
            max_risk_per_trade_percent=max_risk_percent,
            default_rr_ratio=default_rr_ratio,
            min_rr_ratio=min_rr_ratio,
            atr_sl_multiplier=_safe_float(os.getenv("ATR_SL_MULTIPLIER"), 1.2),
            atr_tp_multiplier=_safe_float(os.getenv("ATR_TP_MULTIPLIER"), 2.0),
            use_fixed_risk_amount=_safe_bool(os.getenv("USE_FIXED_RISK_AMOUNT"), False),
            fixed_risk_amount=_safe_float(os.getenv("FIXED_RISK_AMOUNT"), 5.0),
            min_stop_atr_multiplier=min_stop_multiplier,
            max_stop_atr_multiplier=max_stop_multiplier,
            max_spread_to_atr_ratio=max(_safe_float(os.getenv("MAX_SPREAD_TO_ATR_RATIO"), 0.25), 0.0),
            max_spread_cost_risk_percent=max(_safe_float(os.getenv("MAX_SPREAD_COST_RISK_PERCENT"), 20.0), 0.0),
            max_spread_to_sl_ratio=max(_safe_float(os.getenv("MAX_SPREAD_TO_SL_RATIO"), 0.35), 0.0),
            max_spread_to_tp_ratio=max(_safe_float(os.getenv("MAX_SPREAD_TO_TP_RATIO"), 0.25), 0.0),
            min_net_rr_after_spread=_safe_float(os.getenv("MIN_NET_RR_AFTER_SPREAD"), 1.2),
            min_stop_distance_points=max(_safe_float(os.getenv("MIN_STOP_DISTANCE_POINTS"), 0.0), 0.0),
            min_tp_distance_points=max(_safe_float(os.getenv("MIN_TP_DISTANCE_POINTS"), 0.0), 0.0),
            require_eligible_signal_for_execution=_safe_bool(os.getenv("REQUIRE_ELIGIBLE_SIGNAL_FOR_EXECUTION"), True),
            allow_watchlist_plan_preview=_safe_bool(os.getenv("ALLOW_WATCHLIST_PLAN_PREVIEW"), True),
            check_margin_requirement=_safe_bool(os.getenv("CHECK_MARGIN_REQUIREMENT"), True),
            paper_trading_enabled=_safe_bool(os.getenv("PAPER_TRADING_ENABLED"), True),
            paper_trade_eligible_only=_safe_bool(os.getenv("PAPER_TRADE_ELIGIBLE_ONLY"), False),
            paper_include_watchlist=_safe_bool(os.getenv("PAPER_INCLUDE_WATCHLIST"), True),
            paper_journal_path=os.getenv("PAPER_JOURNAL_PATH", "data/logs/paper_trades.csv").strip()
            or "data/logs/paper_trades.csv",
            paper_events_path=os.getenv("PAPER_EVENTS_PATH", "data/logs/paper_trade_events.jsonl").strip()
            or "data/logs/paper_trade_events.jsonl",
            paper_open_trades_snapshot_path=os.getenv(
                "PAPER_OPEN_TRADES_SNAPSHOT_PATH",
                "data/live/paper_trades_open_latest.json",
            ).strip()
            or "data/live/paper_trades_open_latest.json",
            paper_execution_output_path=os.getenv(
                "PAPER_EXECUTION_OUTPUT_PATH",
                "data/live/paper_execution_latest.json",
            ).strip()
            or "data/live/paper_execution_latest.json",
            paper_closed_trades_path=os.getenv("PAPER_CLOSED_TRADES_PATH", "data/logs/paper_trades_closed.csv").strip()
            or "data/logs/paper_trades_closed.csv",
            paper_status_report_path=os.getenv("PAPER_STATUS_REPORT_PATH", "data/live/paper_status_latest.json").strip()
            or "data/live/paper_status_latest.json",
            paper_performance_report_path=os.getenv(
                "PAPER_PERFORMANCE_REPORT_PATH",
                "data/logs/paper_performance_summary.csv",
            ).strip()
            or "data/logs/paper_performance_summary.csv",
            paper_max_open_trades=_safe_bounded_int(os.getenv("PAPER_MAX_OPEN_TRADES"), 5, 1),
            paper_max_open_trades_per_symbol=_safe_bounded_int(os.getenv("PAPER_MAX_OPEN_TRADES_PER_SYMBOL"), 1, 1),
            paper_use_pre_execution_validation=_safe_bool(os.getenv("PAPER_USE_PRE_EXECUTION_VALIDATION"), True),
            paper_commission_per_lot_round_trip=_optional_nonnegative_float(
                os.getenv("PAPER_COMMISSION_PER_LOT_ROUND_TRIP")
            ),
            paper_slippage_points_per_side=_optional_nonnegative_float(
                os.getenv("PAPER_SLIPPAGE_POINTS_PER_SIDE")
            ),
            paper_bot_loop_enabled=_safe_bool(os.getenv("PAPER_BOT_LOOP_ENABLED"), True),
            paper_bot_poll_seconds=_safe_bounded_int(os.getenv("PAPER_BOT_POLL_SECONDS"), 30, 1),
            paper_bot_primary_timeframe=os.getenv("PAPER_BOT_PRIMARY_TIMEFRAME", "M5").strip().upper() or "M5",
            paper_bot_run_on_new_candle_only=_safe_bool(os.getenv("PAPER_BOT_RUN_ON_NEW_CANDLE_ONLY"), True),
            paper_bot_max_cycles=max(_safe_int(os.getenv("PAPER_BOT_MAX_CYCLES"), 0), 0),
            paper_bot_stop_after_closed_trades=_safe_bounded_int(os.getenv("PAPER_BOT_STOP_AFTER_CLOSED_TRADES"), 50, 1),
            paper_bot_status_every_cycles=_safe_bounded_int(os.getenv("PAPER_BOT_STATUS_EVERY_CYCLES"), 1, 1),
            paper_bot_heartbeat_path=os.getenv("PAPER_BOT_HEARTBEAT_PATH", "data/live/paper_bot_heartbeat.json").strip()
            or "data/live/paper_bot_heartbeat.json",
            paper_bot_run_log_path=os.getenv("PAPER_BOT_RUN_LOG_PATH", "data/logs/paper_bot_run.log").strip()
            or "data/logs/paper_bot_run.log",
            paper_bot_analysis_report_path=os.getenv(
                "PAPER_BOT_ANALYSIS_REPORT_PATH",
                "data/live/paper_analysis_latest.json",
            ).strip()
            or "data/live/paper_analysis_latest.json",
            paper_bot_analysis_markdown_path=os.getenv(
                "PAPER_BOT_ANALYSIS_MARKDOWN_PATH",
                "data/logs/paper_analysis_report.md",
            ).strip()
            or "data/logs/paper_analysis_report.md",
            paper_filters_enabled=_safe_bool(os.getenv("PAPER_FILTERS_ENABLED"), False),
            paper_allowed_symbols=[normalize_symbol(value) for value in _parse_csv_list(os.getenv("PAPER_ALLOWED_SYMBOLS"))],
            paper_allowed_timeframes=[value.upper() for value in _parse_csv_list(os.getenv("PAPER_ALLOWED_TIMEFRAMES"))],
            paper_allowed_directions=[value.upper() for value in _parse_csv_list(os.getenv("PAPER_ALLOWED_DIRECTIONS"))],
            paper_min_signal_score=max(_safe_float(os.getenv("PAPER_MIN_SIGNAL_SCORE"), 0.0), 0.0),
            paper_allowed_signal_statuses=[
                value.upper() for value in _parse_csv_list(os.getenv("PAPER_ALLOWED_SIGNAL_STATUSES", "WATCHLIST,ELIGIBLE"))
            ]
            or ["WATCHLIST", "ELIGIBLE"],
            paper_require_costs_valid=_safe_bool(os.getenv("PAPER_REQUIRE_COSTS_VALID"), True),
            paper_require_broker_constraints_valid=_safe_bool(
                os.getenv("PAPER_REQUIRE_BROKER_CONSTRAINTS_VALID"),
                True,
            ),
            paper_experiment_name=os.getenv("PAPER_EXPERIMENT_NAME", "baseline").strip() or "baseline",
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
        )
