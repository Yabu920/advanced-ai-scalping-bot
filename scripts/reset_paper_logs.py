"""Archive paper trading logs so paper testing can restart cleanly."""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAPER_FILES = [
    "data/logs/paper_trades.csv",
    "data/logs/paper_trade_events.jsonl",
    "data/logs/paper_trades_closed.csv",
    "data/logs/paper_performance_summary.csv",
    "data/live/paper_trades_open_latest.json",
    "data/live/paper_execution_latest.json",
    "data/live/paper_status_latest.json",
    "data/live/paper_bot_heartbeat.json",
    "data/logs/paper_bot_run.log",
    "data/live/paper_analysis_latest.json",
    "data/logs/paper_analysis_report.md",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive paper trading logs without deleting them permanently.")
    parser.add_argument("--confirm", action="store_true", help="Required to archive paper trading logs.")
    parser.add_argument("--label", default="", help="Optional experiment label for the archive directory.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.confirm:
        print("Paper log reset not confirmed.")
        print("Run: python scripts/reset_paper_logs.py --confirm")
        print("This archives paper logs; it does not delete them permanently.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = re.sub(r"[^A-Za-z0-9_-]+", "_", args.label.strip()).strip("_")
    suffix = f"_{safe_label}" if safe_label else ""
    archive_dir = PROJECT_ROOT / "data" / "logs" / "archive" / f"paper_logs_{timestamp}{suffix}"
    archive_dir.mkdir(parents=True, exist_ok=True)

    moved = 0
    for relative_path in PAPER_FILES:
        source = PROJECT_ROOT / relative_path
        if not source.exists():
            continue
        target = archive_dir / source.name
        shutil.move(str(source), str(target))
        moved += 1

    print("Paper logs archived.")
    print(f"Archive path: {archive_dir}")
    print(f"Files moved: {moved}")


if __name__ == "__main__":
    main()
