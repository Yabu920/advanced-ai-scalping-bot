from paper.paper_trade import ELIGIBLE_SIGNAL, INVALID, OPEN, WATCHLIST_SIGNAL, build_paper_trade_from_plan


def plan(status: str = "ELIGIBLE") -> dict:
    return {
        "symbol": "EURUSDm",
        "timeframe": "M1",
        "direction": "BUY",
        "signal_status": status,
        "signal_score": 80,
        "valid": True,
        "entry_reference": 1.1,
        "stop_loss": 1.099,
        "take_profit": 1.102,
        "lot_size": 0.1,
        "risk_amount": 5.0,
        "risk_percent": 0.5,
        "rr_ratio": 2.0,
    }


def test_valid_eligible_plan_creates_open_paper_trade() -> None:
    trade = build_paper_trade_from_plan(plan("ELIGIBLE"))
    assert trade["status"] == OPEN
    assert trade["source"] == ELIGIBLE_SIGNAL


def test_valid_watchlist_plan_creates_open_paper_trade() -> None:
    trade = build_paper_trade_from_plan(plan("WATCHLIST"))
    assert trade["status"] == OPEN
    assert trade["source"] == WATCHLIST_SIGNAL


def test_invalid_plan_returns_invalid() -> None:
    bad = plan()
    bad["valid"] = False
    trade = build_paper_trade_from_plan(bad)
    assert trade["status"] == INVALID
    assert trade["issues"]


def test_missing_buy_sell_direction_returns_invalid() -> None:
    bad = plan()
    bad["direction"] = "NO_TRADE"
    trade = build_paper_trade_from_plan(bad)
    assert trade["status"] == INVALID
