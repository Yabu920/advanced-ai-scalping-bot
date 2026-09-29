import json

from journal.signal_tracker import SignalTracker


def sample_signal(status: str) -> dict:
    return {
        "direction": "SELL",
        "status": status,
        "score": 60,
        "max_score": 100,
        "passed_conditions": [],
        "failed_conditions": [],
        "rejection_reasons": [],
        "details": {},
    }


def sample_signals() -> dict:
    return {
        "EURUSDm": {
            "bias": {"bias": "bearish", "confidence": 70},
            "signals": {
                "M1": sample_signal("ELIGIBLE"),
                "M5": sample_signal("WATCHLIST"),
                "M15": sample_signal("REJECTED"),
            },
        }
    }


def test_build_event_creates_signal_decision_event(tmp_path) -> None:
    tracker = SignalTracker(str(tmp_path / "signals.jsonl"))
    event = tracker.build_event("EURUSDm", "M1", sample_signal("ELIGIBLE"), {"bias": "bearish"})
    assert event["event_type"] == "SIGNAL_DECISION"
    assert event["future_outcome"]["status"] == "PENDING"


def test_append_event_creates_jsonl(tmp_path) -> None:
    jsonl_path = tmp_path / "signals.jsonl"
    tracker = SignalTracker(str(jsonl_path))
    tracker.append_event(tracker.build_event("EURUSDm", "M1", sample_signal("ELIGIBLE")))
    line = jsonl_path.read_text(encoding="utf-8").strip()
    assert json.loads(line)["event_type"] == "SIGNAL_DECISION"


def test_append_signals_respects_track_watchlist_false(tmp_path) -> None:
    jsonl_path = tmp_path / "signals.jsonl"
    count = SignalTracker(str(jsonl_path)).append_signals(
        sample_signals(),
        track_watchlist=False,
        track_rejected=True,
    )
    assert count == 2


def test_append_signals_respects_track_rejected_false(tmp_path) -> None:
    jsonl_path = tmp_path / "signals.jsonl"
    count = SignalTracker(str(jsonl_path)).append_signals(
        sample_signals(),
        track_watchlist=True,
        track_rejected=False,
    )
    assert count == 2
