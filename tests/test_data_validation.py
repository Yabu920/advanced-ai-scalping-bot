import pandas as pd

from strategy.data_validation import validate_ohlc_dataframe


def sample_ohlc_df(rows: int = 60) -> pd.DataFrame:
    times = pd.date_range("2026-05-15", periods=rows, freq="min", tz="UTC")
    close = [100 + index for index in range(rows)]
    return pd.DataFrame(
        {
            "time": times,
            "open": close,
            "high": [value + 1 for value in close],
            "low": [value - 1 for value in close],
            "close": close,
            "tick_volume": [100] * rows,
            "spread": [10] * rows,
            "is_closed_candle": [True] * (rows - 1) + [False],
        }
    )


def test_valid_ohlc_dataframe_passes() -> None:
    result = validate_ohlc_dataframe(sample_ohlc_df())
    assert result["valid"] is True
    assert result["issues"] == []


def test_empty_dataframe_fails() -> None:
    result = validate_ohlc_dataframe(pd.DataFrame())
    assert result["valid"] is False
    assert "empty dataframe" in result["issues"]


def test_missing_column_fails() -> None:
    df = sample_ohlc_df().drop(columns=["spread"])
    result = validate_ohlc_dataframe(df)
    assert result["valid"] is False
    assert any("missing columns" in issue for issue in result["issues"])


def test_duplicate_time_fails() -> None:
    df = sample_ohlc_df()
    df.loc[1, "time"] = df.loc[0, "time"]
    result = validate_ohlc_dataframe(df)
    assert result["valid"] is False
    assert "duplicate time" in result["issues"]


def test_invalid_ohlc_high_low_fails() -> None:
    df = sample_ohlc_df()
    df.loc[0, "high"] = df.loc[0, "low"] - 1
    result = validate_ohlc_dataframe(df)
    assert result["valid"] is False
    assert "high below low" in result["issues"]
