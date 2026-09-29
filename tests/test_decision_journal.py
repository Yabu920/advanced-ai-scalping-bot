import csv

from journal.decision_journal import DecisionJournal


def sample_signal(status: str = "WATCHLIST") -> dict:
    return {
        "direction": "SELL",
        "status": status,
        "score": 60,
        "max_score": 100,
        "rejection_reasons": [],
        "passed_conditions": ["Bias supports SELL"],
        "failed_conditions": ["RSI weak"],
        "details": {
            "latest_candle": {
                "time": "2026-05-15T20:00:00+00:00",
                "close": 1.08,
                "rsi_14": 45,
                "ema_20": 1.09,
                "ema_50": 1.10,
                "ema_200": 1.11,
            },
            "timeframe_analysis": {
                "trend": {"trend": "bearish", "strength": "strong"},
                "regime": {"regime": "TRENDING", "tradable": True},
                "spread": {"spread_quality": "good", "spread_points": 12},
                "volatility": {"volatility": "normal", "atr_14": 0.001},
            },
        },
    }


def sample_signals() -> dict:
    return {
        "EURUSDm": {
            "bias": {"bias": "bearish", "confidence": 70},
            "signals": {
                "M1": sample_signal(),
                "M5": sample_signal("REJECTED"),
            },
        }
    }


def test_flatten_signal_record_includes_required_fields(tmp_path) -> None:
    journal = DecisionJournal(str(tmp_path / "journal.csv"))
    record = journal.flatten_signal_record("EURUSDm", "M1", sample_signal(), {"bias": "bearish", "confidence": 70})
    assert record["symbol"] == "EURUSDm"
    assert record["timeframe"] == "M1"
    assert record["direction"] == "SELL"
    assert record["bias"] == "bearish"
    assert record["trend"] == "bearish"


def test_append_record_creates_csv(tmp_path) -> None:
    csv_path = tmp_path / "journal.csv"
    journal = DecisionJournal(str(csv_path))
    record = journal.flatten_signal_record("EURUSDm", "M1", sample_signal(), {"bias": "bearish", "confidence": 70})
    journal.append_record(record)
    assert csv_path.exists()
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["symbol"] == "EURUSDm"


def test_append_signals_appends_one_row_per_signal(tmp_path) -> None:
    csv_path = tmp_path / "journal.csv"
    count = DecisionJournal(str(csv_path)).append_signals(sample_signals())
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8")))
    assert count == 2
    assert len(rows) == 2
