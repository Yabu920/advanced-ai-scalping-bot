from types import SimpleNamespace

from paper.paper_filters import paper_trade_allowed_by_filters


def settings(**overrides) -> SimpleNamespace:
    values = {
        "paper_filters_enabled": True,
        "paper_allowed_symbols": [],
        "paper_allowed_timeframes": [],
        "paper_allowed_directions": [],
        "paper_min_signal_score": 0.0,
        "paper_allowed_signal_statuses": ["WATCHLIST", "ELIGIBLE"],
        "paper_require_costs_valid": True,
        "paper_require_broker_constraints_valid": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def candidate(**overrides) -> dict:
    values = {
        "symbol": "EURUSDm",
        "timeframe": "M5",
        "direction": "SELL",
        "signal_score": 60,
        "signal_status": "WATCHLIST",
        "costs_valid": True,
        "broker_constraints_valid": True,
    }
    values.update(overrides)
    return values


def test_disabled_filters_allow_trade() -> None:
    allowed, reasons = paper_trade_allowed_by_filters(candidate(), settings(paper_filters_enabled=False))
    assert allowed is True
    assert reasons == []


def test_symbol_filter_blocks_disallowed_symbol() -> None:
    allowed, reasons = paper_trade_allowed_by_filters(candidate(), settings(paper_allowed_symbols=["GBPUSDm"]))
    assert allowed is False
    assert "symbol EURUSDM not allowed" in reasons


def test_timeframe_filter_blocks_disallowed_timeframe() -> None:
    allowed, reasons = paper_trade_allowed_by_filters(candidate(), settings(paper_allowed_timeframes=["M1"]))
    assert allowed is False
    assert "timeframe M5 not allowed" in reasons


def test_direction_filter_blocks_buy_when_only_sell_allowed() -> None:
    allowed, reasons = paper_trade_allowed_by_filters(candidate(direction="BUY"), settings(paper_allowed_directions=["SELL"]))
    assert allowed is False
    assert "direction BUY not allowed" in reasons


def test_min_score_filter_blocks_low_score() -> None:
    allowed, reasons = paper_trade_allowed_by_filters(candidate(signal_score=54), settings(paper_min_signal_score=55))
    assert allowed is False
    assert "signal score 54 below paper minimum 55" in reasons


def test_signal_status_filter_blocks_disallowed_status() -> None:
    allowed, reasons = paper_trade_allowed_by_filters(
        candidate(signal_status="WATCHLIST"),
        settings(paper_allowed_signal_statuses=["ELIGIBLE"]),
    )
    assert allowed is False
    assert "signal status WATCHLIST not allowed" in reasons


def test_costs_valid_required_blocks_invalid_cost_plan() -> None:
    allowed, reasons = paper_trade_allowed_by_filters(candidate(costs_valid=False), settings())
    assert allowed is False
    assert "costs invalid" in reasons


def test_broker_constraints_required_blocks_invalid_plan() -> None:
    allowed, reasons = paper_trade_allowed_by_filters(candidate(broker_constraints_valid=False), settings())
    assert allowed is False
    assert "broker constraints invalid" in reasons
