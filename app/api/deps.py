from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.settings import settings


def _parse_keys(raw: str) -> set[str]:
    # Supports comma-separated keys, e.g. "key1,key2,key3"
    keys = {k.strip() for k in raw.split(",")}
    return {k for k in keys if k}


def require_api_key(x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None) -> None:
    """
    Simple API-key protection for Power BI / Postman / Swagger calls.

    - Enable with API_AUTH_ENABLED=true
    - Configure keys with API_KEYS="k1,k2,k3"
    - Client sends header: X-API-Key: <key>
    """
    if not settings.api_auth_enabled:
        return

    allowed = _parse_keys(settings.api_keys or "")
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API auth enabled but API_KEYS is empty",
        )

    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-API-Key")

    # constant-time comparison against all keys
    if not any(secrets.compare_digest(x_api_key, k) for k in allowed):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

