"""Park-centered spatial endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import get_query_service
from app.db.service import QueryService
from app.models.api import ParkNearbySchoolsResponse

router = APIRouter(prefix="/api/v1/parks", tags=["parks"])


@router.get(
    "/{facility_id}/nearby-schools",
    response_model=ParkNearbySchoolsResponse,
)
def nearby_schools(
    service: Annotated[QueryService, Depends(get_query_service)],
    facility_id: Annotated[str, Path(min_length=1, max_length=100)],
    distance_miles: Annotated[float, Query(gt=0, le=10)] = 1.0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ParkNearbySchoolsResponse:
    """Return schools within a radius of one real park-source feature."""

    return ParkNearbySchoolsResponse.model_validate(
        service.park_nearby_schools(
            facility_id=facility_id,
            distance_miles=distance_miles,
            limit=limit,
            offset=offset,
        )
    )
