"""Human-readable summary for journal writes."""


def build_journal_write_summary(csv_count: int, jsonl_count: int, csv_path: str, jsonl_path: str) -> str:
    return "\n".join(
        [
            "Decision Journal Summary",
            "========================",
            f"CSV records appended: {csv_count}",
            f"JSONL events appended: {jsonl_count}",
            f"CSV path: {csv_path}",
            f"JSONL path: {jsonl_path}",
        ]
    )
