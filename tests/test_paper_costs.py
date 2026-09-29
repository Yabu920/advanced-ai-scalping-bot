from types import SimpleNamespace

from paper.paper_costs import estimate_paper_costs


def test_explicit_zero_commission_and_adverse_slippage_cost() -> None:
    assumptions = SimpleNamespace(
        paper_commission_per_lot_round_trip=0.0,
        paper_slippage_points_per_side=2.0,
    )
    result = estimate_paper_costs(
        {"lot_size": 0.1},
        {"point": 0.00001, "trade_tick_size": 0.00001, "trade_tick_value": 1.0},
        assumptions,
    )
    assert result["commission_amount"] == 0.0
    assert result["slippage_cost_amount"] == 0.4


def test_missing_assumptions_are_unknown() -> None:
    result = estimate_paper_costs({"lot_size": 0.1}, {}, SimpleNamespace())
    assert result["commission_amount"] is None
    assert result["slippage_cost_amount"] is None


def test_slippage_needs_broker_tick_specs_when_nonzero() -> None:
    assumptions = SimpleNamespace(paper_slippage_points_per_side=2.0)
    result = estimate_paper_costs({"lot_size": 0.1}, {}, assumptions)
    assert result["slippage_cost_amount"] is None
