from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import Select, and_, func, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.core.errors import QueryBuildError, UnsafeQueryError
from app.core.settings import settings
from app.models.dim_city import DimCity
from app.models.dim_date import DimDate
from app.models.dim_product import DimProduct
from app.models.fact_sales import FactSales
from app.schemas.intent import AnalyticalIntent, DateRange, FilterClause
from app.services.semantic_layer import SemanticLayer
from app.utils.dates import last_n_days, month_range, today_utc, week_range

logger = logging.getLogger(__name__)


_EXPR_RE = re.compile(r"^(?P<fn>sum|count_distinct)\((?P<field>[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)\)$")


@dataclass(frozen=True)
class BuiltQuery:
    stmt: Select
    sql: str
    columns: list[str]


def _field_to_sa(field: str):
    table, col = field.split(".", 1)
    if table == "fact_sales":
        return getattr(FactSales, col)
    if table == "dim_date":
        return getattr(DimDate, col)
    if table == "dim_city":
        return getattr(DimCity, col)
    if table == "dim_product":
        return getattr(DimProduct, col)
    raise QueryBuildError(f"Unknown table in field: {field}")


def _metric_expr_to_sa(expr: str):
    m = _EXPR_RE.match(expr.strip().lower())
    if not m:
        raise QueryBuildError(f"Unsupported metric expression: {expr}")
    field = m.group("field")
    fn = m.group("fn")
    col = _field_to_sa(field)
    if fn == "sum":
        return func.sum(col)
    if fn == "count_distinct":
        return func.count(func.distinct(col))
    raise QueryBuildError(f"Unsupported metric function: {fn}")


def _resolve_date_range(dr: DateRange) -> tuple[date | None, date | None, dict[str, Any]]:
    meta: dict[str, Any] = {"date_range": dr.kind}
    today = today_utc()

    if dr.kind == "last_n_days":
        r = last_n_days(int(dr.n or 30), end=today)
        meta["n_days"] = int(dr.n or 30)
        return r.start, r.end, meta
    if dr.kind == "this_month":
        r = month_range(today)
        return r.start, r.end, meta
    if dr.kind == "previous_month":
        prev_month_anchor = (today.replace(day=1) - timedelta(days=1))
        r = month_range(prev_month_anchor)
        return r.start, r.end, meta
    if dr.kind == "this_week":
        r = week_range(today)
        return r.start, r.end, meta
    if dr.kind == "previous_week":
        prev_week_anchor = today - timedelta(days=7)
        r = week_range(prev_week_anchor)
        return r.start, r.end, meta
    if dr.kind == "custom":
        if not dr.start_date or not dr.end_date:
            raise QueryBuildError("custom date_range requires start_date and end_date")
        return date.fromisoformat(dr.start_date), date.fromisoformat(dr.end_date), meta
    if dr.kind == "all_time":
        return None, None, meta
    raise QueryBuildError(f"Unknown date_range kind: {dr.kind}")


def _apply_filters(
    where_clauses: list[Any],
    intent_filters: list[FilterClause],
    layer: SemanticLayer,
    detected: dict[str, Any],
) -> None:
    for f in intent_filters:
        field = f.field
        if field in layer.dimensions:
            col = _field_to_sa(layer.dimensions[field].field)
        elif "." in field:
            col = _field_to_sa(field)
        else:
            raise QueryBuildError(f"Unknown filter field: {field}")

        if f.op == "eq":
            where_clauses.append(col == f.value)
        elif f.op == "ilike":
            where_clauses.append(col.ilike(str(f.value)))
        elif f.op == "in":
            if not isinstance(f.value, (list, tuple)):
                raise QueryBuildError("IN filter expects list/tuple")
            where_clauses.append(col.in_(list(f.value)))
        else:
            raise QueryBuildError(f"Unsupported filter op: {f.op}")

        detected.setdefault("filters", []).append({"field": field, "op": f.op, "value": f.value})


def build_query(intent: AnalyticalIntent, layer: SemanticLayer) -> tuple[BuiltQuery, dict[str, Any]]:
    if intent.metric not in layer.metrics:
        raise QueryBuildError(f"Unknown metric: {intent.metric}")

    # base FROM fact_sales join dims
    from_clause = FactSales.__table__
    from_clause = from_clause.join(DimDate.__table__, FactSales.date_id == DimDate.date_id)
    from_clause = from_clause.join(DimCity.__table__, FactSales.city_id == DimCity.city_id)
    from_clause = from_clause.join(DimProduct.__table__, FactSales.product_id == DimProduct.product_id)

    metric_def = layer.metrics[intent.metric]
    metric_expr = _metric_expr_to_sa(metric_def.expression).label(intent.metric)

    select_cols: list[Any] = []
    group_cols: list[Any] = []
    out_columns: list[str] = []

    # date grain handling: we always expose a semantic "date" column for trends
    detected: dict[str, Any] = {"metric": intent.metric, "group_by": intent.group_by, "date_grain": intent.date_grain}

    if intent.date_grain != "none":
        if intent.date_grain == "day":
            date_col = DimDate.full_date.label("date")
        elif intent.date_grain == "week":
            date_col = DimDate.week.label("week")
        elif intent.date_grain == "month":
            date_col = DimDate.month.label("month")
        elif intent.date_grain == "year":
            date_col = DimDate.year.label("year")
        else:
            raise QueryBuildError(f"Unsupported date_grain: {intent.date_grain}")
        select_cols.append(date_col)
        group_cols.append(date_col)
        out_columns.append(date_col.key)

    for dim in intent.group_by:
        if dim not in layer.dimensions:
            raise QueryBuildError(f"Unknown dimension: {dim}")
        field = layer.dimensions[dim].field
        col = _field_to_sa(field).label(dim)
        select_cols.append(col)
        group_cols.append(col)
        out_columns.append(dim)

    select_cols.append(metric_expr)
    out_columns.append(intent.metric)

    stmt = select(*select_cols).select_from(from_clause)

    where_clauses: list[Any] = []
    start, end, date_meta = _resolve_date_range(intent.date_range)
    detected.update(date_meta)
    if start and end:
        where_clauses.append(FactSales.order_date.between(start, end))

    _apply_filters(where_clauses, intent.filters, layer, detected)

    if where_clauses:
        stmt = stmt.where(and_(*where_clauses))

    if group_cols:
        stmt = stmt.group_by(*group_cols)

    # ordering
    if intent.question_type in ("ranking",) or intent.top_n:
        stmt = stmt.order_by(metric_expr.asc() if intent.sort_dir == "asc" else metric_expr.desc())
    elif intent.date_grain != "none":
        # order by date grain
        stmt = stmt.order_by(select_cols[0].asc())

    # limit protection
    limit = intent.top_n or settings.default_limit
    limit = min(limit, settings.max_rows)
    stmt = stmt.limit(limit)

    sql = str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    return BuiltQuery(stmt=stmt, sql=sql, columns=out_columns), detected


_UNSAFE_SQL_RE = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|vacuum|analyze)\b|;|--|/\*|\*/",
    re.IGNORECASE,
)


def assert_safe_readonly_sql(sql: str) -> None:
    s = sql.strip()
    if not s.lower().startswith("select"):
        raise UnsafeQueryError("Only SELECT queries are allowed")
    if _UNSAFE_SQL_RE.search(s):
        raise UnsafeQueryError("Potentially unsafe SQL detected")


def run_built_query(db: Session, built: BuiltQuery) -> tuple[list[dict[str, Any]], list[str]]:
    rows = db.execute(built.stmt).mappings().all()
    data = [dict(r) for r in rows]
    return data, built.columns


def run_readonly_sql(db: Session, sql: str) -> tuple[list[dict[str, Any]], list[str]]:
    assert_safe_readonly_sql(sql)
    sql_limited = sql
    # naive limit guard: if no LIMIT, add one
    if re.search(r"\blimit\b", sql, re.IGNORECASE) is None:
        inner = sql.rstrip().rstrip(";")
        sql_limited = f"SELECT * FROM ({inner}) AS q LIMIT {settings.default_limit}"
    rows = db.execute(text(sql_limited)).mappings().all()
    data = [dict(r) for r in rows]
    cols = list(data[0].keys()) if data else []
    return data, cols

