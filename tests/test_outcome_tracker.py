import csv
import json
from types import SimpleNamespace

from learning.outcome_tracker import OutcomeTracker


def signal_event(symbol: str = "EURUSDm", timeframe: str = "M1") -> dict:
    return {
        "event_time_utc": "2026-05-15T12:00:00+00:00",
        "event_type": "SIGNAL_DECISION",
        "symbol": symbol,
        "timeframe": timeframe,
        "signal": {"direction": "BUY", "status": "REJECTED", "score": 50},
        "future_outcome": {"checked": False},
    }


def test_load_recent_signal_events_reads_jsonl(tmp_path) -> None:
    path = tmp_path / "history.jsonl"
    path.write_text(json.dumps(signal_event()) + "\n", encoding="utf-8")
    tracker = OutcomeTracker(str(path), str(tmp_path / "report.csv"))
    events = tracker.load_recent_signal_events(10)
    assert len(events) == 1
    assert events[0]["symbol"] == "EURUSDm"


def test_invalid_json_line_is_ignored(tmp_path) -> None:
    path = tmp_path / "history.jsonl"
    path.write_text("not-json\n" + json.dumps(signal_event()) + "\n", encoding="utf-8")
    tracker = OutcomeTracker(str(path), str(tmp_path / "report.csv"))
    events = tracker.load_recent_signal_events(10)
    assert len(events) == 1


def test_append_outcome_report_creates_csv(tmp_path) -> None:
    report_path = tmp_path / "report.csv"
    tracker = OutcomeTracker(str(tmp_path / "history.jsonl"), str(report_path))
    count = tracker.append_outcome_report(
        [
            {
                "event_time_utc": "2026-05-15T12:00:00+00:00",
                "symbol": "EURUSDm",
                "timeframe": "M1",
                "direction": "BUY",
                "status": "REJECTED",
                "score": 50,
                "rejection_reasons": "BAD_SPREAD",
                "outcome_label": "FAVORABLE_MOVE",
                "learning_label": "MISSED_GOOD_TRADE",
                "mistake_category": "FILTER_TOO_STRICT",
                "first_hit": "FAVORABLE",
                "future_candles_checked": 12,
                "lesson": "test",
            }
        ]
    )
    rows = list(csv.DictReader(report_path.open(newline="", encoding="utf-8")))
    assert count == 1
    assert rows[0]["symbol"] == "EURUSDm"
