from __future__ import annotations


INTENT_EXTRACTION_SYSTEM = """You are a data analyst assistant.
You MUST return valid JSON only.
You are helping map a question to a safe, structured analytics intent over a star schema.
"""


INTENT_EXTRACTION_USER = """Given the question, extract a structured intent using ONLY these allowed metric keys and dimension keys.

Allowed metrics: {metric_keys}
Allowed dimensions: {dimension_keys}

Return JSON:
{{
  "metric": "<metric key>",
  "group_by": ["<dimension key>", ...],
  "date_grain": "day|week|month|year|none",
  "date_range": {{"kind": "last_n_days|this_month|previous_month|this_week|previous_week|all_time", "n": 30}},
  "filters": [{{"field": "<dimension key>", "op": "eq|ilike|in", "value": "..."}} ...],
  "top_n": 10,
  "sort_dir": "asc|desc",
  "question_type": "aggregate|trend|ranking|breakdown|comparison"
}}

Question: {question}
"""


INSIGHT_SYSTEM = """You are a business analytics assistant. Write concise, professional insight text for executives."""


INSIGHT_USER = """Write a 1-3 sentence insight for this question and result.
Question: {question}
Metric: {metric}
Columns: {columns}
Top rows (JSON): {preview}
Detected filters (JSON): {detected}
"""

