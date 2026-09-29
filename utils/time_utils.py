"""Small datetime helpers."""

from __future__ import annotations

from datetime import datetime


def utc_now() -> datetime:
    return datetime.utcnow()


def local_now() -> datetime:
    return datetime.now()


def format_dt(dt: datetime | None) -> str:
    if dt is None:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S")
