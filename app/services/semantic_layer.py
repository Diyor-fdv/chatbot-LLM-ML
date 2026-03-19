from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.core.errors import SemanticLayerError
from app.core.settings import settings
from app.schemas.semantic import SemanticLayerSchema

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MetricDef:
    key: str
    label: str
    expression: str
    fmt: str | None
    synonyms: list[str]


@dataclass(frozen=True)
class DimensionDef:
    key: str
    label: str
    field: str
    data_type: str
    synonyms: list[str]


class SemanticLayer:
    def __init__(self, raw: SemanticLayerSchema):
        self.raw = raw
        self.tables = raw.tables
        self.joins = raw.joins

        self.metrics: dict[str, MetricDef] = {}
        for k, v in (raw.metrics or {}).items():
            self.metrics[k] = MetricDef(
                key=k,
                label=v.get("label", k),
                expression=v["expression"],
                fmt=v.get("format"),
                synonyms=[s.lower() for s in (v.get("synonyms") or [])],
            )

        self.dimensions: dict[str, DimensionDef] = {}
        for k, v in (raw.dimensions or {}).items():
            self.dimensions[k] = DimensionDef(
                key=k,
                label=v.get("label", k),
                field=v["field"],
                data_type=v.get("data_type", "text"),
                synonyms=[s.lower() for s in (v.get("synonyms") or [])],
            )

        self.named_filters: dict[str, dict[str, Any]] = raw.named_filters or {}

    def to_public_schema(self) -> dict[str, Any]:
        return {
            "version": self.raw.version,
            "tables": self.raw.tables,
            "joins": self.raw.joins,
            "metrics": {k: self._metric_public(v) for k, v in self.metrics.items()},
            "dimensions": {k: self._dimension_public(v) for k, v in self.dimensions.items()},
            "named_filters": self.named_filters,
        }

    @staticmethod
    def _metric_public(m: MetricDef) -> dict[str, Any]:
        return {"label": m.label, "expression": m.expression, "format": m.fmt, "synonyms": m.synonyms}

    @staticmethod
    def _dimension_public(d: DimensionDef) -> dict[str, Any]:
        return {"label": d.label, "field": d.field, "data_type": d.data_type, "synonyms": d.synonyms}


_semantic_layer: SemanticLayer | None = None


def load_semantic_layer(path: str | None = None) -> SemanticLayer:
    p = Path(path or settings.semantic_layer_path)
    if not p.exists():
        raise SemanticLayerError(f"Semantic layer file not found: {p}")
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
        schema = SemanticLayerSchema.model_validate(raw)
        layer = SemanticLayer(schema)
        logger.info("Loaded semantic layer from %s", p)
        return layer
    except Exception as e:  # noqa: BLE001
        raise SemanticLayerError(f"Failed to load semantic layer: {e}") from e


def get_semantic_layer() -> SemanticLayer:
    global _semantic_layer
    if _semantic_layer is None:
        _semantic_layer = load_semantic_layer()
    return _semantic_layer


def refresh_semantic_layer() -> SemanticLayer:
    global _semantic_layer
    _semantic_layer = load_semantic_layer()
    return _semantic_layer

