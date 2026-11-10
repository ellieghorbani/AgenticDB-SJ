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
        version=settings.app_version,
        description=(
            "Read-only relational, spatial, and vector database copilot with "
            "allowlisted schema retrieval, deterministic and OpenAI-assisted "
            "typed planning, parameterized SQL generation, independent SQLGlot "
            "AST validation, restricted-role execution, traced tool orchestration, "
            "evidence-backed answers, and configurable local or OpenAI embeddings. "
            "Hosted models never authorize execution and raw SQL is never accepted "
            "from API clients."
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
