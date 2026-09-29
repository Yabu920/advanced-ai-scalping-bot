from types import SimpleNamespace

import pandas as pd

from mt5 import market_data
from mt5.market_data import MarketDataService, rates_are_fresh


def rates(latest_time: int) -> list[dict]:
    return [
        {
            "time": latest_time - 60,
            "open": 1.0,
            "high": 1.1,
            "low": 0.9,
            "close": 1.0,
            "tick_volume": 1,
            "spread": 1,
        },
        {
            "time": latest_time,
            "open": 1.0,
            "high": 1.1,
            "low": 0.9,
            "close": 1.0,
            "tick_volume": 1,
            "spread": 1,
        },
    ]


def test_freshness_uses_broker_tick_time() -> None:
    assert rates_are_fresh(rates(1_000), {"time": 1_060}, "M1", current_time=1_060) is True
    assert rates_are_fresh(rates(1_000), {"time": 10_000}, "M1", current_time=10_000) is False


def test_h1_candle_can_start_before_a_current_tick() -> None:
    assert rates_are_fresh(rates(1_000), {"time": 1_060}, "H1", current_time=1_060) is True


def test_stale_cached_tick_cannot_make_stale_candles_look_current() -> None:
    assert rates_are_fresh(rates(1_000), {"time": 1_060}, "M1", current_time=10_000) is False


def test_get_rates_retries_stale_history_then_accepts_current_data(monkeypatch) -> None:
    responses = iter([rates(1_000), rates(1_990)])
    monkeypatch.setattr(market_data.mt5, "symbol_info", lambda symbol: SimpleNamespace(visible=True))
    monkeypatch.setattr(market_data.mt5, "copy_rates_from_pos", lambda *args: responses.__next__())
    monkeypatch.setattr(market_data.mt5, "symbol_info_tick", lambda symbol: SimpleNamespace(time=2_000))
    monkeypatch.setattr(market_data.time, "time", lambda: 2_000)

    result = MarketDataService(sleep_fn=lambda seconds: None).get_rates("EURUSDm", "M1", 2)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert result["time"].iloc[-1] == pd.Timestamp(1_990, unit="s", tz="UTC")


def test_get_rates_rejects_history_that_remains_stale(monkeypatch) -> None:
    monkeypatch.setattr(market_data.mt5, "symbol_info", lambda symbol: SimpleNamespace(visible=True))
    monkeypatch.setattr(market_data.mt5, "copy_rates_from_pos", lambda *args: rates(1_000))
    monkeypatch.setattr(market_data.mt5, "symbol_info_tick", lambda symbol: SimpleNamespace(time=10_000))
    monkeypatch.setattr(market_data.time, "time", lambda: 10_000)

    result = MarketDataService(sleep_fn=lambda seconds: None).get_rates("EURUSDm", "M1", 2)

    assert result.empty
