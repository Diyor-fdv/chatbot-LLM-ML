from __future__ import annotations

from fastapi import APIRouter

from app.services.semantic_layer import refresh_semantic_layer

router = APIRouter()


@router.post("/refresh-semantic-layer")
def refresh_semantic():
    layer = refresh_semantic_layer()
    return {"status": "refreshed", "version": layer.raw.version}

