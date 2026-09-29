from config.settings import (
    Settings,
    _optional_nonnegative_float,
    _parse_symbols,
    _parse_timeframes,
    _safe_int,
)


def test_parsing_comma_separated_symbols() -> None:
    assert _parse_symbols("XAUUSDm, EURUSDm,, GBPUSDm ", "XAUUSD") == [
        "XAUUSDm",
        "EURUSDm",
        "GBPUSDm",
    ]


def test_parsing_comma_separated_timeframes() -> None:
    assert _parse_timeframes("m1, M5,, h1 ", "M5") == ["M1", "M5", "H1"]


def test_invalid_bars_per_timeframe_fallback() -> None:
    assert _safe_int("not-a-number", 500) == 500
    assert _safe_int("-10", 500) == 500


def test_optional_paper_cost_assumptions_preserve_zero_and_unknown() -> None:
    assert _optional_nonnegative_float("0") == 0.0
    assert _optional_nonnegative_float("") is None
    assert _optional_nonnegative_float("-1") is None
    assert _optional_nonnegative_float("nan") is None


def test_environment_loads_explicit_paper_costs(monkeypatch) -> None:
    monkeypatch.setenv("PAPER_COMMISSION_PER_LOT_ROUND_TRIP", "0")
    monkeypatch.setenv("PAPER_SLIPPAGE_POINTS_PER_SIDE", "2.5")
    loaded = Settings.load()
    assert loaded.paper_commission_per_lot_round_trip == 0.0
    assert loaded.paper_slippage_points_per_side == 2.5


def test_environment_loads_sell_only_paper_experiment(monkeypatch) -> None:
    experiment = {
        "PAPER_FILTERS_ENABLED": "true",
        "PAPER_ALLOWED_SYMBOLS": "EURUSDm,GBPUSDm",
        "PAPER_ALLOWED_TIMEFRAMES": "M5",
        "PAPER_ALLOWED_DIRECTIONS": "SELL",
        "PAPER_MIN_SIGNAL_SCORE": "55",
        "PAPER_ALLOWED_SIGNAL_STATUSES": "WATCHLIST,ELIGIBLE",
        "PAPER_REQUIRE_COSTS_VALID": "true",
        "PAPER_REQUIRE_BROKER_CONSTRAINTS_VALID": "true",
        "PAPER_EXPERIMENT_NAME": "m5_sell_only",
    }
    for key, value in experiment.items():
        monkeypatch.setenv(key, value)

    loaded = Settings.load()

    assert loaded.paper_filters_enabled is True
    assert loaded.paper_allowed_symbols == ["EURUSDm", "GBPUSDm"]
    assert loaded.paper_allowed_timeframes == ["M5"]
    assert loaded.paper_allowed_directions == ["SELL"]
    assert loaded.paper_min_signal_score == 55
    assert loaded.paper_allowed_signal_statuses == ["WATCHLIST", "ELIGIBLE"]
    assert loaded.paper_require_costs_valid is True
    assert loaded.paper_require_broker_constraints_valid is True
    assert loaded.paper_experiment_name == "m5_sell_only"
