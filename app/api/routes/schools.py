"""School-centered spatial endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_query_service
from app.db.service import QueryService
from app.models.api import SchoolNearParkResponse

router = APIRouter(prefix="/api/v1/schools", tags=["schools"])


@router.get("/near-open-parks", response_model=SchoolNearParkResponse)
def schools_near_open_parks(
    service: Annotated[QueryService, Depends(get_query_service)],
    distance_miles: Annotated[float, Query(gt=0, le=10)] = 1.0,
    education_level_code: Annotated[
        str | None,
        Query(min_length=1, max_length=20),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SchoolNearParkResponse:
    """Find in-scope schools whose nearest open park feature is within a radius."""

    items, total = service.schools_near_open_parks(
        distance_miles=distance_miles,
        education_level_code=education_level_code,
        limit=limit,
        offset=offset,
    )
    normalized_level = (
        education_level_code.upper() if education_level_code is not None else None
    )
    return SchoolNearParkResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        requested_distance_miles=distance_miles,
        education_level_code=normalized_level,
    )
