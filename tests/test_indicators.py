import pandas as pd

from strategy.indicators import add_basic_indicators, atr, ema, rsi


def sample_df() -> pd.DataFrame:
    values = list(range(1, 31))
    return pd.DataFrame(
        {
            "open": values,
            "high": [value + 1 for value in values],
            "low": [value - 1 for value in values],
            "close": values,
            "tick_volume": [100] * len(values),
            "spread": [10] * len(values),
        }
    )


def test_ema_returns_same_length_as_input() -> None:
    df = sample_df()
    result = ema(df["close"], 20)
    assert len(result) == len(df)


def test_rsi_returns_same_length_as_input() -> None:
    df = sample_df()
    result = rsi(df["close"], 14)
    assert len(result) == len(df)


def test_atr_returns_same_length_as_input() -> None:
    df = sample_df()
    result = atr(df, 14)
    assert len(result) == len(df)


def test_add_basic_indicators_adds_expected_columns() -> None:
    df = sample_df()
    result = add_basic_indicators(df)
    expected_columns = {"ema_20", "ema_50", "ema_200", "rsi_14", "atr_14"}
    assert expected_columns.issubset(result.columns)


def test_add_basic_indicators_handles_empty_dataframe() -> None:
    df = pd.DataFrame(columns=["open", "high", "low", "close", "tick_volume", "spread"])
    result = add_basic_indicators(df)
    assert result.empty
    assert {"ema_20", "ema_50", "ema_200", "rsi_14", "atr_14"}.issubset(result.columns)
