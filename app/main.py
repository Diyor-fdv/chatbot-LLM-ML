from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.logging import configure_logging
from app.core.settings import settings
from app.services.semantic_layer import get_semantic_layer


def create_app() -> FastAPI:
    configure_logging(settings.log_level)

    app = FastAPI(
        title="AI Analytics Chatbot (Power BI Ready)",
        version="0.1.0",
        description="Safe analytics chatbot: NL question → structured intent → safe SQL → Power BI-ready response.",
    )

    # CORS for local Power BI / dev tooling
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.on_event("startup")
    def _startup() -> None:
        # warm semantic layer
        get_semantic_layer()

    return app


app = create_app()

