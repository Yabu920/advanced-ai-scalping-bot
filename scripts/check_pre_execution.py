"""Stage 8 broker constraints and trading cost validation diagnostics."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import Settings
from mt5.connection import MT5Connection
from mt5.market_data import MarketDataService
from mt5.symbols import SymbolService
from risk.pre_execution_summary import build_pre_execution_summary
from risk.pre_execution_validator import PreExecutionValidator
from risk.trade_plan import TradePlanBuilder
from risk.trade_plan_summary import build_trade_plan_summary
from strategy.market_analyzer import MarketAnalyzer
from strategy.signal_engine import SignalEngine
from strategy.signal_summary import build_signal_summary
from utils.logger import setup_logger


def to_json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): to_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [to_json_safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def save_validation_json(validation: dict[str, Any]) -> Path:
    output_dir = PROJECT_ROOT / "data" / "live"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "pre_execution_validation_latest.json"
    output_path.write_text(json.dumps(to_json_safe(validation), indent=2), encoding="utf-8")
    return output_path


def main() -> int:
    settings = Settings.load()
    logger = setup_logger(__name__, settings.log_level)

    print("Advanced AI Scalping Bot - Stage 8 Pre-Execution Validation")
    print("This script validates broker constraints and trading costs only. It does not place trades.")

    connection = MT5Connection(settings)
    if not connection.initialize():
        message = "MT5 connection failed. Run python scripts/check_mt5_connection.py for details."
        logger.error(message)
        print(message)
        return 1

    try:
        market_data = MarketDataService(settings.log_level)
        data = market_data.get_multi_symbol_rates(settings.symbols, settings.timeframes, settings.bars_per_timeframe)
        spread_map = {symbol: market_data.get_spread_points(symbol) for symbol in data}
        analysis = MarketAnalyzer().analyze_market(data, spread_map)
        signals = SignalEngine().generate_market_signals(data, analysis, settings)

        account_info = connection.get_account_info() or {}
        symbol_service = SymbolService()
        symbol_info_map = {symbol: symbol_service.get_symbol_info(symbol) or {"name": symbol} for symbol in data}
        plans = TradePlanBuilder(settings).build_plans_from_signals(signals, account_info, symbol_info_map)
        validation = PreExecutionValidator().validate_plans(plans, symbol_info_map, account_info, spread_map, settings)
        output_path = save_validation_json(validation)

        print()
        print(build_signal_summary(signals))
        print()
        print(build_trade_plan_summary(plans))
        print()
        print(build_pre_execution_summary(validation))
        print()
        print(f"Saved pre-execution validation JSON: {output_path}")
        logger.info("Stage 8 pre-execution validation completed. Saved JSON to %s.", output_path)
        return 0
    except Exception as exc:
        logger.exception("Stage 8 pre-execution validation failed safely: %s", exc)
        print(f"Pre-execution validation failed safely: {exc}")
        return 1
    finally:
        connection.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
