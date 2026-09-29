"""Run the Stage 10 continuous paper trading loop."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import Settings
from paper.paper_bot_runner import PaperBotRunner
from paper.paper_filters import paper_filter_summary
from utils.logger import setup_logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the continuous paper trading bot.")
    parser.add_argument("--max-cycles", type=int, default=None, help="Override PAPER_BOT_MAX_CYCLES.")
    parser.add_argument("--stop-after-closed-trades", type=int, default=None, help="Override PAPER_BOT_STOP_AFTER_CLOSED_TRADES.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings.load()
    logger = setup_logger(__name__, settings.log_level)

    print("Advanced AI Scalping Bot - Stage 10 Continuous Paper Runner")
    print("This is paper simulation only. It does not place MT5 orders.")
    print("Press Ctrl+C to stop.")
    print()
    print("# Paper Filter Configuration")
    print()
    print(f"Experiment: {settings.paper_experiment_name}")
    print(f"Filters enabled: {str(settings.paper_filters_enabled).lower()}")
    print(f"Allowed symbols: {', '.join(settings.paper_allowed_symbols) or 'any'}")
    print(f"Allowed timeframes: {', '.join(settings.paper_allowed_timeframes) or 'any'}")
    print(f"Allowed directions: {', '.join(settings.paper_allowed_directions) or 'any'}")
    print(f"Min signal score: {settings.paper_min_signal_score:g}")
    print(f"Allowed statuses: {', '.join(settings.paper_allowed_signal_statuses) or 'any'}")
    print(f"Valid costs required: {str(settings.paper_require_costs_valid).lower()}")
    print(f"Valid broker constraints required: {str(settings.paper_require_broker_constraints_valid).lower()}")
    print(f"Active filters: {paper_filter_summary(settings)}")

    runner = PaperBotRunner(settings, logger=logger)
    return runner.run(args.max_cycles, args.stop_after_closed_trades)


if __name__ == "__main__":
    raise SystemExit(main())
