from paper.paper_performance import calculate_paper_performance


def closed_trades() -> list[dict]:
    return [
        {"symbol": "EURUSDm", "timeframe": "M1", "pnl_amount": 10.0, "pnl_r": 2.0},
        {"symbol": "EURUSDm", "timeframe": "M5", "pnl_amount": -5.0, "pnl_r": -1.0},
        {"symbol": "GBPUSDm", "timeframe": "M1", "pnl_amount": 10.0, "pnl_r": 2.0},
    ]


def test_win_loss_count() -> None:
    result = calculate_paper_performance(closed_trades())
    assert result["wins"] == 2
    assert result["losses"] == 1


def test_win_rate() -> None:
    result = calculate_paper_performance(closed_trades())
    assert round(result["win_rate"], 1) == 66.7


def test_total_r() -> None:
    result = calculate_paper_performance(closed_trades())
    assert result["total_r"] == 3.0


def test_by_symbol_grouping() -> None:
    result = calculate_paper_performance(closed_trades())
    assert result["by_symbol"]["EURUSDm"]["total_closed"] == 2


def test_by_timeframe_grouping() -> None:
    result = calculate_paper_performance(closed_trades())
    assert result["by_timeframe"]["M1"]["total_closed"] == 2


def test_cost_completeness_is_explicit() -> None:
    trades = closed_trades()
    trades[0]["cost_model_complete"] = True
    result = calculate_paper_performance(trades)
    assert result["complete_cost_trades"] == 1
    assert result["incomplete_cost_trades"] == 2
