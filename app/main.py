"""FastAPI application factory for AgenticDB-SJ."""

import logging

import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import __version__
from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import ResourceNotFoundError
from app.models.api import RootResponse

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Provenance-aware natural-language database copilot over real "
            "relational, geospatial, and vector data. AgenticDB-SJ combines "
            "OpenAI structured planning, allowlisted deterministic SQL, "
            "independent SQLGlot AST validation, restricted read-only "
            "PostgreSQL/PostGIS execution, pgvector HNSW retrieval, traced "
            "tool orchestration, and evidence-backed answers. Raw SQL is "
            "never accepted from API clients."
        ),
    )

    @application.get("/", response_model=RootResponse, tags=["root"])
    def root() -> RootResponse:
        return RootResponse(
            service=settings.app_name,
            version=__version__,
            docs="/docs",
            health="/health/ready",
        )

    @application.exception_handler(ResourceNotFoundError)
    async def handle_not_found(
        request: Request,
        exc: ResourceNotFoundError,
    ) -> JSONResponse:
        del request
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @application.exception_handler(psycopg.Error)
    async def handle_database_error(
        request: Request,
        exc: psycopg.Error,
    ) -> JSONResponse:
        logger.exception("Database request failed", exc_info=exc)
        del request
        return JSONResponse(
            status_code=503,
            content={"detail": "Database service is unavailable."},
        )

    application.include_router(api_router)
    return application


app = create_app()
