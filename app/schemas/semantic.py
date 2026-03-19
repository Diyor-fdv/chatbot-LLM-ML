from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SemanticLayerSchema(BaseModel):
    version: int
    tables: dict[str, Any]
    joins: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    dimensions: dict[str, Any] = Field(default_factory=dict)
    named_filters: dict[str, Any] = Field(default_factory=dict)

