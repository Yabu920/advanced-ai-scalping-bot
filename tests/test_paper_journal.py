import json

from paper.paper_journal import PaperJournal
from paper.paper_trade import CLOSED_TP, OPEN


def trade(status: str = OPEN) -> dict:
    return {
        "paper_trade_id": "paper-1",
        "created_time_utc": "2026-05-20T00:00:00+00:00",
        "symbol": "EURUSDm",
        "timeframe": "M1",
        "direction": "BUY",
        "source": "WATCHLIST_SIGNAL",
        "status": status,
        "entry_price": 1.1,
        "stop_loss": 1.099,
        "take_profit": 1.102,
        "lot_size": 0.1,
        "risk_amount": 5.0,
        "risk_percent": 0.5,
        "rr_ratio": 2.0,
        "signal_score": 60,
        "signal_status": "WATCHLIST",
    }


def journal(tmp_path) -> PaperJournal:
    return PaperJournal(
        str(tmp_path / "paper.csv"),
        str(tmp_path / "paper.jsonl"),
        str(tmp_path / "open.json"),
    )


def test_append_trades_creates_csv_and_jsonl(tmp_path) -> None:
    j = journal(tmp_path)
    assert j.append_trades([trade()]) == 1
    assert (tmp_path / "paper.csv").exists()
    assert (tmp_path / "paper.jsonl").exists()


def test_load_open_trades_returns_only_open_trades(tmp_path) -> None:
    j = journal(tmp_path)
    j.append_trade_events([trade(OPEN)], "PAPER_TRADE_OPENED")
    j.append_trade_events([trade(CLOSED_TP)], "PAPER_TRADE_CLOSED")
    assert j.load_open_trades() == []


def test_save_snapshot_creates_json_file(tmp_path) -> None:
    j = journal(tmp_path)
    j.save_snapshot([trade(OPEN), trade(CLOSED_TP)])
    data = json.loads((tmp_path / "open.json").read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["status"] == OPEN


def test_reconstruct_latest_trade_states_keeps_latest_event_per_trade_id(tmp_path) -> None:
    j = journal(tmp_path)
    j.append_trade_events([trade(OPEN)], "PAPER_TRADE_OPENED")
    j.append_trade_events([trade(CLOSED_TP)], "PAPER_TRADE_CLOSED")
    states = j.reconstruct_latest_trade_states()
    assert states["paper-1"]["status"] == CLOSED_TP


def test_get_current_open_trades_returns_only_open(tmp_path) -> None:
    j = journal(tmp_path)
    open_trade = trade(OPEN)
    open_trade["paper_trade_id"] = "paper-open"
    closed_trade = trade(CLOSED_TP)
    closed_trade["paper_trade_id"] = "paper-closed"
    j.append_trade_events([open_trade], "PAPER_TRADE_OPENED")
    j.append_trade_events([closed_trade], "PAPER_TRADE_CLOSED")
    result = j.get_current_open_trades()
    assert len(result) == 1
    assert result[0]["paper_trade_id"] == "paper-open"


def test_get_closed_trades_returns_only_closed(tmp_path) -> None:
    j = journal(tmp_path)
    open_trade = trade(OPEN)
    open_trade["paper_trade_id"] = "paper-open"
    closed_trade = trade(CLOSED_TP)
    closed_trade["paper_trade_id"] = "paper-closed"
    j.append_trade_events([open_trade], "PAPER_TRADE_OPENED")
    j.append_trade_events([closed_trade], "PAPER_TRADE_CLOSED")
    result = j.get_closed_trades()
    assert len(result) == 1
    assert result[0]["paper_trade_id"] == "paper-closed"


def test_append_closed_trades_csv_avoids_duplicates(tmp_path) -> None:
    j = journal(tmp_path)
    path = tmp_path / "closed.csv"
    closed = trade(CLOSED_TP)
    assert j.append_closed_trades_csv([closed], str(path)) == 1
    assert j.append_closed_trades_csv([closed], str(path)) == 0
