from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass(frozen=True)
class ResolvedDateRange:
    start: date | None
    end: date | None  # inclusive


def today_utc() -> date:
    # For MVP; can be replaced with timezone-aware handling.
    return datetime.utcnow().date()


def last_n_days(n: int, *, end: date | None = None) -> ResolvedDateRange:
    if n <= 0:
        raise ValueError("n must be > 0")
    end_d = end or today_utc()
    start_d = end_d - timedelta(days=n - 1)
    return ResolvedDateRange(start=start_d, end=end_d)


def month_range(target: date) -> ResolvedDateRange:
    start = target.replace(day=1)
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1)
    else:
        next_month = start.replace(month=start.month + 1)
    end = next_month - timedelta(days=1)
    return ResolvedDateRange(start=start, end=end)


def week_range(target: date) -> ResolvedDateRange:
    # Monday-based ISO week.
    start = target - timedelta(days=target.weekday())
    end = start + timedelta(days=6)
    return ResolvedDateRange(start=start, end=end)

