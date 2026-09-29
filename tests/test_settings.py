from config.settings import Settings, _parse_symbols, _parse_timeframes, _safe_int


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


def test_project_env_loads_sell_only_paper_experiment(monkeypatch) -> None:
    for key in (
        "PAPER_FILTERS_ENABLED",
        "PAPER_ALLOWED_SYMBOLS",
        "PAPER_ALLOWED_TIMEFRAMES",
        "PAPER_ALLOWED_DIRECTIONS",
        "PAPER_MIN_SIGNAL_SCORE",
        "PAPER_ALLOWED_SIGNAL_STATUSES",
        "PAPER_REQUIRE_COSTS_VALID",
        "PAPER_REQUIRE_BROKER_CONSTRAINTS_VALID",
        "PAPER_EXPERIMENT_NAME",
    ):
        monkeypatch.delenv(key, raising=False)

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
