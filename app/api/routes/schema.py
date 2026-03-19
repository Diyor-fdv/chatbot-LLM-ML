from __future__ import annotations

from fastapi import APIRouter

from app.services.semantic_layer import get_semantic_layer

router = APIRouter()


@router.get("/schema")
def get_schema():
    layer = get_semantic_layer()
    return layer.to_public_schema()

