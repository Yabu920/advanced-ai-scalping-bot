import pandas as pd

from learning.outcome_types import (
    ADVERSE_MOVE,
    BAD_ELIGIBLE_SIGNAL,
    CORRECT_REJECTION,
    FAVORABLE_MOVE,
    INSUFFICIENT_FUTURE_DATA,
    MISSED_GOOD_TRADE,
    NO_CLEAR_MOVE,
)
from learning.signal_outcome import calculate_future_outcome, classify_signal_learning_result


def signal(direction: str = "BUY", status: str = "REJECTED") -> dict:
    return {
        "direction": direction,
        "status": status,
        "details": {
            "latest_candle": {
                "time": "2026-05-15T12:00:00+00:00",
                "close": 100.0,
                "atr_14": 10.0,
            }
        },
    }


def future_df(highs: list[float], lows: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": pd.date_range("2026-05-15T12:01:00Z", periods=len(highs), freq="min"),
            "high": highs,
            "low": lows,
            "is_closed_candle": [True] * len(highs),
        }
    )


def test_buy_favorable_move_returns_favorable_move() -> None:
    result = calculate_future_outcome(signal("BUY"), future_df([111, 112], [99, 100]), 2, 1.0, 0.7)
    assert result["outcome_label"] == FAVORABLE_MOVE


def test_sell_favorable_move_returns_favorable_move() -> None:
    result = calculate_future_outcome(signal("SELL"), future_df([101, 100], [89, 88]), 2, 1.0, 0.7)
    assert result["outcome_label"] == FAVORABLE_MOVE


def test_buy_adverse_move_returns_adverse_move() -> None:
    result = calculate_future_outcome(signal("BUY"), future_df([101, 102], [92, 90]), 2, 1.0, 0.7)
    assert result["outcome_label"] == ADVERSE_MOVE


def test_sell_adverse_move_returns_adverse_move() -> None:
    result = calculate_future_outcome(signal("SELL"), future_df([108, 109], [99, 98]), 2, 1.0, 0.7)
    assert result["outcome_label"] == ADVERSE_MOVE


def test_no_clear_move_returns_no_clear_move() -> None:
    result = calculate_future_outcome(signal("BUY"), future_df([104, 105], [96, 95]), 2, 1.0, 0.7)
    assert result["outcome_label"] == NO_CLEAR_MOVE


def test_insufficient_future_data_returns_insufficient_future_data() -> None:
    result = calculate_future_outcome(signal("BUY"), future_df([104], [96]), 2, 1.0, 0.7)
    assert result["outcome_label"] == INSUFFICIENT_FUTURE_DATA


def test_rejected_favorable_move_classifies_as_missed_good_trade() -> None:
    result = classify_signal_learning_result({"status": "REJECTED"}, {"outcome_label": FAVORABLE_MOVE})
    assert result["learning_label"] == MISSED_GOOD_TRADE


def test_rejected_adverse_move_classifies_as_correct_rejection() -> None:
    result = classify_signal_learning_result({"status": "REJECTED"}, {"outcome_label": ADVERSE_MOVE})
    assert result["learning_label"] == CORRECT_REJECTION


def test_eligible_adverse_move_classifies_as_bad_eligible_signal() -> None:
    result = classify_signal_learning_result({"status": "ELIGIBLE"}, {"outcome_label": ADVERSE_MOVE})
    assert result["learning_label"] == BAD_ELIGIBLE_SIGNAL
