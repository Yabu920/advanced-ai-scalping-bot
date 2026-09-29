"""Explicit, optional execution-cost assumptions for paper trades."""

from __future__ import annotations

import math
from typing import Any


def _nonnegative(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) and parsed >= 0 else None


def estimate_paper_costs(plan: dict, symbol_info: dict | None, settings: Any) -> dict[str, float | None]:
    """Quote round-trip commission and adverse slippage in account currency.

    Both inputs must be explicitly configured. A missing input stays unknown.
    """
    lot = _nonnegative(plan.get("lot_size"))
    commission_rate = _nonnegative(getattr(settings, "paper_commission_per_lot_round_trip", None))
    slippage_points = _nonnegative(getattr(settings, "paper_slippage_points_per_side", None))
    info = symbol_info or {}
    point = _nonnegative(info.get("point"))
    tick_size = _nonnegative(info.get("trade_tick_size"))
    tick_value = _nonnegative(info.get("trade_tick_value"))

    commission = lot * commission_rate if lot is not None and lot > 0 and commission_rate is not None else None
    slippage = None
    if lot is not None and lot > 0 and slippage_points is not None:
        if slippage_points == 0:
            slippage = 0.0
        elif point is not None and point > 0 and tick_size is not None and tick_size > 0 and tick_value is not None and tick_value > 0:
            # Adverse movement on both entry and exit, independent of spread.
            slippage = 2 * slippage_points * point / tick_size * tick_value * lot

    return {
        "commission_amount": commission,
        "slippage_points_per_side": slippage_points,
        "slippage_cost_amount": slippage,
    }
