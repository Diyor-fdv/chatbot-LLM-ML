from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


TimeGrain = Literal["day", "week", "month", "year", "none"]
SortDirection = Literal["asc", "desc"]


@dataclass(frozen=True)
class DateRange:
    kind: Literal[
        "last_n_days",
        "this_month",
        "previous_month",
        "this_week",
        "previous_week",
        "custom",
        "all_time",
    ] = "all_time"
    n: int | None = None
    start_date: str | None = None  # YYYY-MM-DD
    end_date: str | None = None  # YYYY-MM-DD


@dataclass(frozen=True)
class FilterClause:
    field: str  # semantic dimension name or explicit field like dim_city.city_name
    op: Literal["eq", "ilike", "in"] = "eq"
    value: Any = None


@dataclass(frozen=True)
class AnalyticalIntent:
    metric: str  # semantic metric key (e.g., revenue, profit, orders)
    group_by: list[str]
    date_grain: TimeGrain
    date_range: DateRange
    filters: list[FilterClause]
    top_n: int | None = None
    sort_by: str | None = None  # metric or dimension name
    sort_dir: SortDirection = "desc"
    comparison: Literal["none", "previous_period"] = "none"
    question_type: Literal["aggregate", "trend", "ranking", "breakdown", "comparison"] = "aggregate"

