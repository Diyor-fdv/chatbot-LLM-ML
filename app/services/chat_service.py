from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.llm.client import LLMMessage, llm_chat
from app.llm.prompts import INSIGHT_SYSTEM, INSIGHT_USER, INTENT_EXTRACTION_SYSTEM, INTENT_EXTRACTION_USER
from app.schemas.chat import ChatAskResponse, KPISet
from app.schemas.intent import AnalyticalIntent, DateRange, FilterClause
from app.services.chart_recommender import powerbi_visual_spec, recommend_chart
from app.services.insight import compute_kpis, generate_insight_text
from app.services.intent_parser import parse_intent
from app.services.query_builder import build_query, run_built_query
from app.services.semantic_layer import get_semantic_layer

logger = logging.getLogger(__name__)


def _llm_try_extract_intent(question: str, *, metric_keys: list[str], dimension_keys: list[str]) -> dict[str, Any] | None:
    prompt = INTENT_EXTRACTION_USER.format(
        metric_keys=", ".join(metric_keys),
        dimension_keys=", ".join(dimension_keys),
        question=question,
    )
    try:
        raw = llm_chat(
            [LLMMessage(role="system", content=INTENT_EXTRACTION_SYSTEM), LLMMessage(role="user", content=prompt)]
        )
        if not raw:
            return None
        return json.loads(raw)
    except Exception as e:  # noqa: BLE001
        logger.warning("LLM intent extraction failed; falling back to rules. err=%s", e)
        return None


def _coerce_llm_intent(raw: dict[str, Any], *, metric_keys: set[str], dimension_keys: set[str]) -> AnalyticalIntent | None:
    try:
        metric = str(raw.get("metric", "")).strip()
        if metric not in metric_keys:
            return None

        group_by = [g for g in (raw.get("group_by") or []) if isinstance(g, str) and g in dimension_keys]

        dg = raw.get("date_grain", "none")
        if dg not in ("day", "week", "month", "year", "none"):
            dg = "none"

        dr_raw = raw.get("date_range") or {}
        kind = dr_raw.get("kind", "all_time")
        n = dr_raw.get("n")
        if kind == "last_n_days" and not isinstance(n, int):
            n = 30
        if kind not in ("last_n_days", "this_month", "previous_month", "this_week", "previous_week", "all_time"):
            kind = "all_time"
        date_range = DateRange(kind=kind, n=n if kind == "last_n_days" else None)  # type: ignore[arg-type]

        filters: list[FilterClause] = []
        for f in raw.get("filters") or []:
            if not isinstance(f, dict):
                continue
            field = f.get("field")
            if not isinstance(field, str) or field not in dimension_keys:
                continue
            op = f.get("op", "eq")
            if op not in ("eq", "ilike", "in"):
                op = "eq"
            value = f.get("value")
            filters.append(FilterClause(field=field, op=op, value=value))

        top_n = raw.get("top_n")
        if not isinstance(top_n, int):
            top_n = None
        if top_n is not None:
            top_n = max(1, min(top_n, 100))

        sort_dir = raw.get("sort_dir", "desc")
        if sort_dir not in ("asc", "desc"):
            sort_dir = "desc"

        qt = raw.get("question_type", "aggregate")
        if qt not in ("aggregate", "trend", "ranking", "breakdown", "comparison"):
            qt = "aggregate"

        return AnalyticalIntent(
            metric=metric,
            group_by=group_by,
            date_grain=dg,  # type: ignore[arg-type]
            date_range=date_range,
            filters=filters,
            top_n=top_n,
            sort_by=metric if qt == "ranking" else None,
            sort_dir=sort_dir,  # type: ignore[arg-type]
            comparison="previous_period" if qt == "comparison" else "none",  # type: ignore[arg-type]
            question_type=qt,  # type: ignore[arg-type]
        )
    except Exception:  # noqa: BLE001
        return None


def _llm_try_polish_insight(question: str, intent: AnalyticalIntent, columns: list[str], data: list[dict[str, Any]], detected: dict[str, Any]) -> str | None:
    preview = data[:5]
    prompt = INSIGHT_USER.format(
        question=question,
        metric=intent.metric,
        columns=columns,
        preview=json.dumps(preview, ensure_ascii=False),
        detected=json.dumps(detected, ensure_ascii=False),
    )
    try:
        raw = llm_chat(
            [LLMMessage(role="system", content=INSIGHT_SYSTEM), LLMMessage(role="user", content=prompt)],
            temperature=0.2,
        )
        return raw.strip() if raw else None
    except Exception as e:  # noqa: BLE001
        logger.warning("LLM insight polish failed; using templates. err=%s", e)
        return None


def answer_question(db: Session, question: str, context: dict[str, Any] | None = None) -> ChatAskResponse:
    layer = get_semantic_layer()

    # intent: rules-first, optional LLM assist
    intent = parse_intent(question, layer=layer)

    llm_raw = _llm_try_extract_intent(question, metric_keys=list(layer.metrics.keys()), dimension_keys=list(layer.dimensions.keys()))
    if llm_raw:
        llm_intent = _coerce_llm_intent(llm_raw, metric_keys=set(layer.metrics.keys()), dimension_keys=set(layer.dimensions.keys()))
        if llm_intent:
            intent = llm_intent

    built, detected = build_query(intent, layer)
    data, columns = run_built_query(db, built)

    chart_type, chart_title = recommend_chart(intent, columns)

    kpi_vals = compute_kpis(intent, data) if chart_type == "kpi" or intent.question_type in ("aggregate", "comparison") else {}
    kpis = KPISet(values=kpi_vals) if kpi_vals else None

    answer_text = generate_insight_text(intent, data, detected)
    polished = _llm_try_polish_insight(question, intent, columns, data, detected)
    if polished:
        answer_text = polished

    filters_detected: dict[str, Any] = {
        "date_range": detected.get("date_range"),
        "n_days": detected.get("n_days"),
        "filters": detected.get("filters", []),
    }

    powerbi = {
        "visual": powerbi_visual_spec(chart_type, columns, intent),
        "dataset": {"columns": columns, "rows": len(data)},
        "suggested_measures": [intent.metric],
        "suggested_dimensions": [c for c in columns if c != intent.metric],
    }

    warnings: list[str] = []
    if len(data) >= 0 and intent.top_n is None and len(data) == settings.default_limit:
        warnings.append(f"Result limited to {settings.default_limit} rows (DEFAULT_LIMIT).")

    return ChatAskResponse(
        question=question,
        answer_text=answer_text,
        chart_type=chart_type,
        chart_title=chart_title,
        kpis=kpis,
        filters_detected=filters_detected,
        columns=columns,
        data=data,
        generated_sql=built.sql,
        confidence=0.85 if llm_raw else 0.75,
        warnings=warnings,
        powerbi=powerbi,
    )

