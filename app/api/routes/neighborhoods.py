"""Neighborhood metric and detail endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import get_query_service
from app.db.service import QueryService
from app.models.api import NeighborhoodListResponse, NeighborhoodSummaryResponse

router = APIRouter(prefix="/api/v1/neighborhoods", tags=["neighborhoods"])


@router.get("", response_model=NeighborhoodListResponse)
def list_neighborhoods(
    service: Annotated[QueryService, Depends(get_query_service)],
    min_schools: Annotated[int, Query(ge=0)] = 0,
    min_open_park_features: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> NeighborhoodListResponse:
    """List neighborhoods with school and open-park-feature counts."""

    items, total = service.list_neighborhoods(
        min_schools=min_schools,
        min_open_park_features=min_open_park_features,
        limit=limit,
        offset=offset,
    )
    return NeighborhoodListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{neighborhood_id}", response_model=NeighborhoodSummaryResponse)
def neighborhood_summary(
    service: Annotated[QueryService, Depends(get_query_service)],
    neighborhood_id: Annotated[str, Path(min_length=1, max_length=100)],
) -> NeighborhoodSummaryResponse:
    """Return one neighborhood's area and database-derived counts."""

    return NeighborhoodSummaryResponse.model_validate(
        service.neighborhood_summary(neighborhood_id)
    )
