from __future__ import annotations

from typing import Any

import pandas as pd

from app.schemas.intent import AnalyticalIntent


def compute_kpis(intent: AnalyticalIntent, data: list[dict[str, Any]]) -> dict[str, float]:
    if not data:
        return {}
    df = pd.DataFrame(data)
    metric = intent.metric
    if metric not in df.columns:
        return {}
    if len(df.columns) == 1:
        val = float(df.iloc[0][metric])
        return {f"total_{metric}": val}
    # default KPI: total metric across returned rows
    return {f"total_{metric}": float(df[metric].sum())}


def generate_insight_text(intent: AnalyticalIntent, data: list[dict[str, Any]], detected: dict[str, Any]) -> str:
    metric_label = intent.metric.replace("_", " ").title()
    if not data:
        return f"No data found for {metric_label} with the detected filters."

    df = pd.DataFrame(data)
    metric = intent.metric

    if intent.question_type == "trend" and metric in df.columns and df.shape[0] >= 2:
        first = float(df.iloc[0][metric])
        last = float(df.iloc[-1][metric])
        if first == 0:
            return f"{metric_label} trend returned {df.shape[0]} points. Latest value is {last:,.2f}."
        change_pct = (last - first) / abs(first) * 100.0
        direction = "increased" if change_pct >= 0 else "decreased"
        return f"{metric_label} {direction} by {abs(change_pct):.1f}% over the selected period (from {first:,.2f} to {last:,.2f})."

    if intent.question_type in ("ranking",) and metric in df.columns:
        dim_cols = [c for c in df.columns if c != metric]
        if dim_cols:
            best_row = df.iloc[0] if intent.sort_dir == "desc" else df.iloc[-1]
            dim_name = dim_cols[0].replace("_", " ").title()
            return f"{best_row[dim_cols[0]]} leads by {metric_label} with {float(best_row[metric]):,.2f} ({dim_name} ranking)."

    if intent.question_type == "aggregate":
        val = float(df.iloc[0][metric]) if metric in df.columns else None
        if val is not None:
            return f"Total {metric_label} is {val:,.2f} for the selected filters."

    return f"Here are the results for {metric_label} based on your question."

