"""Symbol configuration helpers."""

DEFAULT_SYMBOLS = ["XAUUSD", "EURUSD", "GBPUSD"]


def normalize_symbol(symbol: str) -> str:
    """Normalize a user or broker symbol without changing broker suffixes."""
    return symbol.strip()


def is_supported_symbol(symbol: str) -> bool:
    """Return whether the exact base symbol is in the Stage 1 support list.

    Some brokers use suffixes such as XAUUSDm or EURUSDm. Stage 1 does not block
    those in runtime data collection, but this helper currently checks exact base
    symbols only. Suffix-aware matching can be added in a later stage.
    """
    return normalize_symbol(symbol).upper() in DEFAULT_SYMBOLS
