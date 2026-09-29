"""Build a clean paper performance analysis report."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import Settings
from paper.paper_analysis import analyze_closed_paper_trades
from paper.paper_analysis_summary import build_paper_analysis_markdown
from paper.paper_journal import PaperJournal


def main() -> int:
    settings = Settings.load()
    journal = PaperJournal(
        settings.paper_journal_path,
        settings.paper_events_path,
        settings.paper_open_trades_snapshot_path,
    )
    closed_trades = journal.get_closed_trades()
    if not closed_trades:
        print("No closed paper trades found. Run python scripts/run_paper_bot.py or scripts/check_paper_execution.py first.")
        return 1

    analysis = analyze_closed_paper_trades(closed_trades)
    markdown = build_paper_analysis_markdown(analysis)
    journal.save_execution_output(analysis, settings.paper_bot_analysis_report_path)
    output_path = Path(settings.paper_bot_analysis_markdown_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    print(markdown)
    print()
    print(f"Analysis JSON: {settings.paper_bot_analysis_report_path}")
    print(f"Analysis markdown: {settings.paper_bot_analysis_markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
