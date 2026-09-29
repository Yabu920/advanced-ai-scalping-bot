"""Stage 3 market analysis diagnostics."""

from __future__ import annotations

import json
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
from strategy.market_analyzer import MarketAnalyzer
from strategy.market_summary import build_market_analysis_summary
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
    if pd.isna(value) if not isinstance(value, (dict, list, tuple)) else False:
        return None
    return value


def save_analysis_json(analysis: dict[str, Any]) -> Path:
    output_dir = PROJECT_ROOT / "data" / "live"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "market_analysis_latest.json"
    output_path.write_text(json.dumps(to_json_safe(analysis), indent=2), encoding="utf-8")
    return output_path


def main() -> int:
    settings = Settings.load()
    logger = setup_logger(__name__, settings.log_level)

    print("Advanced AI Scalping Bot - Stage 3 Market Analysis")
    print("This script analyzes market conditions only. It does not place trades.")

    connection = MT5Connection(settings)
    if not connection.initialize():
        message = "MT5 connection failed. Run python scripts/check_mt5_connection.py for details."
        logger.error(message)
        print(message)
        return 1

    try:
        market_data = MarketDataService(settings.log_level)
        data = market_data.get_multi_symbol_rates(
            settings.symbols,
            settings.timeframes,
            settings.bars_per_timeframe,
        )
        spread_map = {
            symbol: market_data.get_spread_points(symbol)
            for symbol in data
        }

        analyzer = MarketAnalyzer()
        analysis = analyzer.analyze_market(data, spread_map)
        summary = build_market_analysis_summary(analysis)
        output_path = save_analysis_json(analysis)

        logger.info("Stage 3 market analysis completed. Saved JSON to %s.", output_path)
        print()
        print(summary)
        print()
        print(f"Saved analysis JSON: {output_path}")
        return 0 if analysis else 1
    except Exception as exc:
        logger.exception("Stage 3 market analysis failed safely: %s", exc)
        print(f"Market analysis failed safely: {exc}")
        return 1
    finally:
        connection.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
