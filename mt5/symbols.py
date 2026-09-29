"""Symbol metadata helpers for MetaTrader 5."""

from __future__ import annotations

from typing import Any

import MetaTrader5 as mt5


SYMBOL_INFO_FIELDS = [
    "name",
    "path",
    "description",
    "visible",
    "trade_mode",
    "point",
    "digits",
    "spread",
    "volume_min",
    "volume_max",
    "volume_step",
    "trade_stops_level",
    "trade_freeze_level",
    "trade_tick_size",
    "trade_tick_value",
    "trade_contract_size",
    "margin_initial",
    "margin_maintenance",
]


class SymbolService:
    """Read clean symbol metadata from MT5 without raising on missing fields."""

    def get_symbol_info(self, symbol: str) -> dict[str, Any] | None:
        info = mt5.symbol_info(symbol)
        if info is None:
            return None
        return {field: getattr(info, field, None) for field in SYMBOL_INFO_FIELDS}
