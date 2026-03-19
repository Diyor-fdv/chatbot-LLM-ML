from __future__ import annotations

import re
from datetime import timedelta

from app.schemas.intent import AnalyticalIntent, DateRange, FilterClause
from app.services.semantic_layer import SemanticLayer, get_semantic_layer


_TOP_N_RE = re.compile(r"\btop\s+(?P<n>\d{1,3})\b", re.IGNORECASE)
_LAST_N_DAYS_RE = re.compile(r"\blast\s+(?P<n>\d{1,3})\s+days\b", re.IGNORECASE)


def _detect_metric(question: str, layer: SemanticLayer) -> str:
    q = question.lower()
    # direct mention of metric key
    for key in layer.metrics.keys():
        if re.search(rf"\b{re.escape(key)}\b", q):
            return key
    # synonyms
    for key, m in layer.metrics.items():
        for syn in m.synonyms:
            if syn and syn in q:
                return key
    return "revenue"


def _detect_group_bys(question: str, layer: SemanticLayer) -> list[str]:
    q = question.lower()
    group_bys: list[str] = []
    for key, d in layer.dimensions.items():
        if re.search(rf"\b{re.escape(key)}\b", q):
            group_bys.append(key)
            continue
        for syn in d.synonyms:
            if syn and syn in q:
                group_bys.append(key)
                break
    # normalize: don't include duplicate
    seen: set[str] = set()
    out: list[str] = []
    for g in group_bys:
        if g not in seen:
            out.append(g)
            seen.add(g)
    return out


def _detect_date_range(question: str) -> DateRange:
    q = question.lower()
    m = _LAST_N_DAYS_RE.search(q)
    if m:
        n = int(m.group("n"))
        return DateRange(kind="last_n_days", n=n)
    if "last week" in q:
        return DateRange(kind="previous_week")
    if "this week" in q:
        return DateRange(kind="this_week")
    if "previous month" in q or "last month" in q:
        return DateRange(kind="previous_month")
    if "this month" in q or "current month" in q:
        return DateRange(kind="this_month")
    if "last 30 days" in q:
        return DateRange(kind="last_n_days", n=30)
    if "last 7 days" in q:
        return DateRange(kind="last_n_days", n=7)
    return DateRange(kind="all_time")


def _detect_top_n(question: str) -> int | None:
    m = _TOP_N_RE.search(question)
    if not m:
        return None
    n = int(m.group("n"))
    return max(1, min(n, 100))


def _detect_filters(question: str, layer: SemanticLayer) -> list[FilterClause]:
    q = question.lower()
    filters: list[FilterClause] = []

    # Named filters (simple keywords)
    for name, f in layer.named_filters.items():
        if name.lower() in q:
            filters.append(FilterClause(field=f["field"], op=f.get("op", "eq"), value=f.get("value")))

    # Region/city basic "in <value>" patterns
    # e.g. "in Tashkent" or "only Tashkent"
    city_match = re.search(r"\b(in|only)\s+(?P<city>[a-zA-Z\s\-']{3,40})\b", question, re.IGNORECASE)
    if city_match:
        candidate = city_match.group("city").strip()
        # heuristic: if user says "region", map to region; else city
        if "region" in q:
            filters.append(FilterClause(field="region", op="ilike", value=f"%{candidate}%"))
        else:
            filters.append(FilterClause(field="city", op="ilike", value=f"%{candidate}%"))

    # Category filter: "category <x>" or "in <x> category"
    cat_match = re.search(r"\bcategory\s+(?P<cat>[a-zA-Z\s\-']{3,40})\b", question, re.IGNORECASE)
    if cat_match:
        candidate = cat_match.group("cat").strip()
        filters.append(FilterClause(field="category", op="ilike", value=f"%{candidate}%"))

    return filters


def _detect_question_type(question: str, group_by: list[str], date_range: DateRange, top_n: int | None) -> str:
    q = question.lower()
    if any(w in q for w in ["compare", "vs", "versus"]) and (("this month" in q) or ("previous month" in q) or ("last month" in q)):
        return "comparison"
    if top_n is not None or any(w in q for w in ["top", "highest", "lowest", "underperformed", "best", "worst"]):
        return "ranking" if group_by else "aggregate"
    if date_range.kind != "all_time" and ("trend" in q or "over time" in q or "daily" in q or "last" in q):
        return "trend"
    if group_by:
        return "breakdown"
    return "aggregate"


def _detect_date_grain(question: str, question_type: str) -> str:
    q = question.lower()
    if "weekly" in q or "by week" in q:
        return "week"
    if "monthly" in q or "by month" in q:
        return "month"
    if "yearly" in q or "by year" in q:
        return "year"
    if question_type == "trend":
        return "day"
    return "none"


def parse_intent(question: str, layer: SemanticLayer | None = None) -> AnalyticalIntent:
    layer = layer or get_semantic_layer()

    metric = _detect_metric(question, layer)
    group_by = _detect_group_bys(question, layer)
    date_range = _detect_date_range(question)
    top_n = _detect_top_n(question)
    filters = _detect_filters(question, layer)

    question_type = _detect_question_type(question, group_by, date_range, top_n)
    date_grain = _detect_date_grain(question, question_type)

    comparison = "previous_period" if question_type == "comparison" else "none"

    # Sorting default: metric desc for ranking
    sort_by = metric if question_type in ("ranking",) else None
    sort_dir = "desc"

    # If user asks "lowest" -> asc
    if re.search(r"\blowest\b|\bsmallest\b|\bunderperformed\b|\bworst\b", question.lower()):
        sort_dir = "asc"

    return AnalyticalIntent(
        metric=metric,
        group_by=group_by,
        date_grain=date_grain,  # type: ignore[arg-type]
        date_range=date_range,
        filters=filters,
        top_n=top_n,
        sort_by=sort_by,
        sort_dir=sort_dir,  # type: ignore[arg-type]
        comparison=comparison,  # type: ignore[arg-type]
        question_type=question_type,  # type: ignore[arg-type]
    )

