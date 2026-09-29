from types import SimpleNamespace

from paper.paper_engine import PaperExecutionEngine
from paper.paper_trade import CLOSED_SL, CLOSED_TP, OPEN


def settings(**overrides) -> SimpleNamespace:
    base = {
        "paper_trading_enabled": True,
        "paper_trade_eligible_only": False,
        "paper_include_watchlist": True,
        "paper_max_open_trades": 5,
        "paper_max_open_trades_per_symbol": 2,
        "paper_use_pre_execution_validation": True,
        "paper_filters_enabled": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def plan(status: str = "WATCHLIST") -> dict:
    return {
        "symbol": "EURUSDm",
        "timeframe": "M5",
        "direction": "SELL",
        "signal_score": 60,
        "signal_status": status,
        "valid": True,
    }


def validation(**overrides) -> dict:
    base = {"plan_valid": True, "broker_constraints_valid": True, "costs_valid": True, "execution_ready_later": False}
    base.update(overrides)
    return base


def trade(direction: str = "BUY") -> dict:
    return {
        "paper_trade_id": "1",
        "symbol": "EURUSDm",
        "timeframe": "M5",
        "direction": direction,
        "status": OPEN,
        "entry_price": 100,
        "stop_loss": 95 if direction == "BUY" else 105,
        "take_profit": 110 if direction == "BUY" else 90,
        "risk_amount": 5.0,
        "rr_ratio": 2.0,
    }


def test_should_reject_when_paper_trading_disabled() -> None:
    result = PaperExecutionEngine(settings(paper_trading_enabled=False)).should_create_paper_trade(plan(), validation(), [])
    assert result["allowed"] is False


def test_should_allow_watchlist_when_enabled_and_validation_passes() -> None:
    result = PaperExecutionEngine(settings()).should_create_paper_trade(plan("WATCHLIST"), validation(), [])
    assert result["allowed"] is True


def sell_only_settings(**overrides) -> SimpleNamespace:
    return settings(
        paper_filters_enabled=True,
        paper_allowed_symbols=["EURUSDm", "GBPUSDm"],
        paper_allowed_timeframes=["M5"],
        paper_allowed_directions=["SELL"],
        paper_min_signal_score=55,
        paper_allowed_signal_statuses=["WATCHLIST", "ELIGIBLE"],
        paper_require_costs_valid=True,
        paper_require_broker_constraints_valid=True,
        paper_experiment_name="m5_sell_only",
        **overrides,
    )


def test_sell_only_experiment_rejects_buy_before_trade_creation() -> None:
    buy_plan = {**plan(), "direction": "BUY"}
    engine = PaperExecutionEngine(sell_only_settings())

    trades = engine.create_paper_trades_from_plans(
        {"EURUSDm": {"M5": buy_plan}},
        {"EURUSDm": {"M5": validation()}},
        [],
    )

    assert trades == []
    assert engine.last_candidate_decisions[0]["paper_filter_reasons"] == ["direction BUY not allowed"]


def test_sell_only_experiment_accepts_sell_and_saves_label() -> None:
    engine = PaperExecutionEngine(sell_only_settings())

    trades = engine.create_paper_trades_from_plans(
        {"EURUSDm": {"M5": plan()}},
        {"EURUSDm": {"M5": validation()}},
        [],
    )

    assert len(trades) == 1
    assert trades[0]["direction"] == "SELL"
    assert trades[0]["paper_experiment_name"] == "m5_sell_only"
    assert "directions=SELL" in trades[0]["paper_filter_summary"]


def test_should_reject_watchlist_when_eligible_only() -> None:
    result = PaperExecutionEngine(settings(paper_trade_eligible_only=True)).should_create_paper_trade(plan("WATCHLIST"), validation(), [])
    assert result["allowed"] is False


def test_should_reject_duplicate_open_trade_same_symbol_timeframe() -> None:
    result = PaperExecutionEngine(settings()).should_create_paper_trade(plan("WATCHLIST"), validation(), [trade()])
    assert result["allowed"] is False


def test_buy_tp_hit_closes_as_tp() -> None:
    result = PaperExecutionEngine(settings()).update_open_trade_with_candle(trade("BUY"), {"high": 111, "low": 99, "time": "t"})
    assert result["status"] == CLOSED_TP


def test_buy_sl_hit_closes_as_sl() -> None:
    result = PaperExecutionEngine(settings()).update_open_trade_with_candle(trade("BUY"), {"high": 101, "low": 94, "time": "t"})
    assert result["status"] == CLOSED_SL


def test_sell_tp_hit_closes_as_tp() -> None:
    result = PaperExecutionEngine(settings()).update_open_trade_with_candle(trade("SELL"), {"high": 101, "low": 89, "time": "t"})
    assert result["status"] == CLOSED_TP


def test_sell_sl_hit_closes_as_sl() -> None:
    result = PaperExecutionEngine(settings()).update_open_trade_with_candle(trade("SELL"), {"high": 106, "low": 99, "time": "t"})
    assert result["status"] == CLOSED_SL


def test_same_candle_tp_and_sl_closes_as_sl_conservative() -> None:
    result = PaperExecutionEngine(settings()).update_open_trade_with_candle(trade("BUY"), {"high": 111, "low": 94, "time": "t"})
    assert result["status"] == CLOSED_SL


def test_tp_pnl_subtracts_validated_spread_cost() -> None:
    open_trade = {
        **trade("BUY"),
        "spread_cost_known": True,
        "spread_cost_amount": 0.5,
    }
    result = PaperExecutionEngine(settings()).update_open_trade_with_candle(
        open_trade,
        {"high": 111, "low": 99, "time": "t"},
    )
    assert result["gross_pnl_amount"] == 10.0
    assert result["total_cost_amount"] == 0.5
    assert result["pnl_amount"] == 9.5
    assert result["pnl_r"] == 1.9
    assert result["pnl_basis"] == "NET_AFTER_SPREAD"


def test_sl_pnl_includes_validated_spread_cost() -> None:
    open_trade = {
        **trade("BUY"),
        "spread_cost_known": True,
        "spread_cost_amount": 0.5,
    }
    result = PaperExecutionEngine(settings()).update_open_trade_with_candle(
        open_trade,
        {"high": 101, "low": 94, "time": "t"},
    )
    assert result["gross_pnl_amount"] == -5.0
    assert result["pnl_amount"] == -5.5
    assert result["pnl_r"] == -1.1
    assert result["pnl_basis"] == "NET_AFTER_SPREAD"


def test_complete_cost_model_deducts_spread_commission_and_slippage() -> None:
    open_trade = {
        **trade("BUY"),
        "spread_cost_known": True,
        "spread_cost_amount": 0.5,
        "commission_amount": 0.0,
        "slippage_cost_amount": 0.4,
    }
    result = PaperExecutionEngine(settings()).update_open_trade_with_candle(
        open_trade, {"high": 111, "low": 99, "time": "t"}
    )
    assert result["gross_pnl_amount"] == 10.0
    assert result["total_cost_amount"] == 0.9
    assert result["pnl_amount"] == 9.1
    assert round(result["pnl_r"], 2) == 1.82
    assert result["cost_model_complete"] is True
    assert result["pnl_basis"] == "NET_AFTER_MODELED_COSTS"


def test_missing_commission_and_slippage_labels_partial_pnl() -> None:
    open_trade = {
        **trade("BUY"),
        "spread_cost_known": True,
        "spread_cost_amount": 0.5,
    }
    result = PaperExecutionEngine(settings()).update_open_trade_with_candle(
        open_trade, {"high": 111, "low": 99, "time": "t"}
    )
    assert result["pnl_amount"] == 9.5
    assert result["cost_model_complete"] is False
    assert result["pnl_basis"] == "NET_AFTER_SPREAD"
    assert any("not fully cost-adjusted" in issue for issue in result["issues"])


def test_created_trade_carries_cost_assumptions_through_close() -> None:
    proposed = {
        **plan(), "lot_size": 0.1, "risk_amount": 5.0, "rr_ratio": 2.0,
        "entry_reference": 100, "stop_loss": 105, "take_profit": 90,
    }
    checked = {
        **validation(), "checks": {"costs": {"spread_cost": {"known": True, "spread_cost": 0.5}}}
    }
    engine = PaperExecutionEngine(settings(
        paper_commission_per_lot_round_trip=0.0,
        paper_slippage_points_per_side=2.0,
    ))
    created = engine.create_paper_trades_from_plans(
        {"EURUSDm": {"M5": proposed}}, {"EURUSDm": {"M5": checked}}, [],
        {"EURUSDm": {"point": 0.00001, "trade_tick_size": 0.00001, "trade_tick_value": 1.0}},
    )[0]
    closed = engine.update_open_trade_with_candle(
        created, {"high": 104, "low": 89, "time": "2099-01-01T00:00:00Z"}
    )
    assert closed["status"] == CLOSED_TP
    assert closed["cost_model_complete"] is True
    assert closed["total_cost_amount"] == 0.9
    assert closed["pnl_amount"] == 9.1
