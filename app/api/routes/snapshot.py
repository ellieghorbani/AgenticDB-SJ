"""Fixed-snapshot metadata endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_query_service
from app.db.service import QueryService
from app.models.api import SnapshotResponse

router = APIRouter(prefix="/api/v1", tags=["snapshot"])


@router.get("/snapshot", response_model=SnapshotResponse)
def snapshot(
    service: Annotated[QueryService, Depends(get_query_service)],
) -> SnapshotResponse:
    """Return counts that identify the currently loaded database snapshot."""

    return SnapshotResponse.model_validate(service.snapshot())
