from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ChartType = Literal["line", "bar", "column", "table", "kpi", "donut", "matrix"]


class ChatAskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    context: dict[str, Any] | None = None


class KPISet(BaseModel):
    values: dict[str, float] = Field(default_factory=dict)


class ChatAskResponse(BaseModel):
    question: str
    answer_text: str
    chart_type: ChartType
    chart_title: str
    kpis: KPISet | None = None
    filters_detected: dict[str, Any] = Field(default_factory=dict)
    columns: list[str] = Field(default_factory=list)
    data: list[dict[str, Any]] = Field(default_factory=list)
    generated_sql: str | None = None
    confidence: float = 0.5
    warnings: list[str] = Field(default_factory=list)
    powerbi: dict[str, Any] = Field(default_factory=dict)

