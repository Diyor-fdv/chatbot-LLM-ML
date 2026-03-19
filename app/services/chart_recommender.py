from __future__ import annotations

from typing import Any

from app.schemas.chat import ChartType
from app.schemas.intent import AnalyticalIntent


def recommend_chart(intent: AnalyticalIntent, columns: list[str]) -> tuple[ChartType, str]:
    # Deterministic rules based on intent + result shape.
    metric = intent.metric.replace("_", " ").title()

    if intent.question_type == "comparison":
        # usually 2 periods -> column chart or KPI with delta; for MVP return column
        return "column", f"{metric} - This vs Previous Period"

    if len(columns) == 1:
        return "kpi", f"Total {metric}"

    if intent.date_grain != "none" and ("date" in columns or "week" in columns or "month" in columns or "year" in columns):
        return "line", f"{metric} Trend"

    if intent.top_n is not None or intent.question_type == "ranking":
        return "bar", f"Top {intent.top_n or ''} {metric}".strip()

    # breakdowns
    if len(columns) == 2:
        dim = columns[0].replace("_", " ").title()
        return "column", f"{metric} by {dim}"

    # If many columns -> table
    return "table", f"{metric} Details"


def powerbi_visual_spec(chart_type: ChartType, columns: list[str], intent: AnalyticalIntent) -> dict[str, Any]:
    # Simple metadata contract Power BI (or a client) can map to visuals.
    spec: dict[str, Any] = {"visual": chart_type, "encoding": {}}
    metric = intent.metric

    if chart_type == "kpi":
        spec["encoding"] = {"value": metric}
        return spec

    if chart_type in ("line",):
        spec["encoding"] = {"x": columns[0], "y": metric}
        return spec

    if chart_type in ("bar", "column", "donut"):
        spec["encoding"] = {"category": columns[0], "value": metric}
        return spec

    if chart_type in ("table", "matrix"):
        spec["encoding"] = {"columns": columns}
        return spec

    return spec

