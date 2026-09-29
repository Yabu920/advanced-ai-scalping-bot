from paper.paper_analysis import analyze_closed_paper_trades


def trades() -> list[dict]:
    return [
        {
            "symbol": "GBPUSDm",
            "timeframe": "M5",
            "direction": "BUY",
            "signal_status": "WATCHLIST",
            "source": "WATCHLIST_SIGNAL",
            "signal_score": 60,
            "pnl_r": 2.0,
            "pnl_amount": 10.0,
            "close_time_utc": "2026-06-10T10:00:00+00:00",
        },
        {
            "symbol": "GBPUSDm",
            "timeframe": "M5",
            "direction": "SELL",
            "signal_status": "WATCHLIST",
            "source": "WATCHLIST_SIGNAL",
            "signal_score": 55,
            "pnl_r": -1.0,
            "pnl_amount": -5.0,
            "close_time_utc": "2026-06-10T11:00:00+00:00",
        },
        {
            "symbol": "EURUSDm",
            "timeframe": "M1",
            "direction": "SELL",
            "signal_status": "WATCHLIST",
            "source": "WATCHLIST_SIGNAL",
            "signal_score": 55,
            "pnl_r": -1.0,
            "pnl_amount": -5.0,
            "close_time_utc": "2026-06-10T12:00:00+00:00",
        },
        {
            "symbol": "EURUSDm",
            "timeframe": "M5",
            "direction": "SELL",
            "signal_status": "WATCHLIST",
            "source": "WATCHLIST_SIGNAL",
            "signal_score": 60,
            "pnl_r": 2.0,
            "pnl_amount": 10.0,
            "close_time_utc": "2026-06-10T13:00:00+00:00",
        },
    ]


def test_calculates_win_rate() -> None:
    result = analyze_closed_paper_trades(trades())
    assert result["win_rate"] == 50.0


def test_calculates_total_r() -> None:
    result = analyze_closed_paper_trades(trades())
    assert result["total_r"] == 2.0


def test_calculates_average_r() -> None:
    result = analyze_closed_paper_trades(trades())
    assert result["average_r"] == 0.5


def test_calculates_profit_factor() -> None:
    result = analyze_closed_paper_trades(trades())
    assert result["profit_factor"] == 2.0


def test_groups_by_symbol() -> None:
    result = analyze_closed_paper_trades(trades())
    assert result["by_symbol"]["GBPUSDm"]["trades"] == 2


def test_groups_by_timeframe() -> None:
    result = analyze_closed_paper_trades(trades())
    assert result["by_timeframe"]["M5"]["trades"] == 3


def test_groups_by_direction() -> None:
    result = analyze_closed_paper_trades(trades())
    assert result["by_direction"]["SELL"]["trades"] == 3


def test_calculates_max_consecutive_losses() -> None:
    result = analyze_closed_paper_trades(trades())
    assert result["max_consecutive_losses"] == 2


def test_calculates_max_drawdown_in_r() -> None:
    result = analyze_closed_paper_trades(trades())
    assert result["max_drawdown_r"] == -2.0


def test_groups_by_experiment_name() -> None:
    sample = trades()
    sample[0]["paper_experiment_name"] = "m5_sell_only"
    result = analyze_closed_paper_trades(sample)
    assert result["by_experiment"]["m5_sell_only"]["trades"] == 1


def test_missing_experiment_name_defaults_to_baseline() -> None:
    result = analyze_closed_paper_trades(trades())
    assert result["by_experiment"]["baseline"]["trades"] == 4
