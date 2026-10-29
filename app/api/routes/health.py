"""Process and database health endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app import __version__
from app.api.dependencies import get_query_service
from app.db.service import QueryService
from app.models.api import LiveHealthResponse, ReadyHealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=LiveHealthResponse)
def live() -> LiveHealthResponse:
    """Confirm that the API process can serve requests."""

    return LiveHealthResponse(
        status="ok",
        service="AgenticDB-SJ API",
        version=__version__,
    )


@router.get("/ready", response_model=ReadyHealthResponse)
def ready(
    service: Annotated[QueryService, Depends(get_query_service)],
) -> ReadyHealthResponse:
    """Confirm PostgreSQL connectivity and the PostGIS extension."""

    return ReadyHealthResponse.model_validate(service.readiness())
