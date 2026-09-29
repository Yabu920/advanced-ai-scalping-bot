from paper.paper_monitor import calculate_floating_metrics


def buy_trade() -> dict:
    return {"direction": "BUY", "entry_price": 100.0, "stop_loss": 95.0, "take_profit": 110.0, "risk_amount": 5.0}


def sell_trade() -> dict:
    return {"direction": "SELL", "entry_price": 100.0, "stop_loss": 105.0, "take_profit": 90.0, "risk_amount": 5.0}


def test_buy_floating_metrics_positive_when_price_above_entry() -> None:
    result = calculate_floating_metrics(buy_trade(), 103.0)
    assert result["floating_r"] > 0
    assert result["floating_pnl_estimate"] > 0


def test_sell_floating_metrics_positive_when_price_below_entry() -> None:
    result = calculate_floating_metrics(sell_trade(), 97.0)
    assert result["floating_r"] > 0
    assert result["floating_pnl_estimate"] > 0


def test_distance_to_tp_and_sl_calculated_correctly() -> None:
    result = calculate_floating_metrics(buy_trade(), 103.0)
    assert result["distance_to_tp"] == 7.0
    assert result["distance_to_sl"] == 8.0
