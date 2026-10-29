"""Typed response contracts for the AgenticDB-SJ API."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RootResponse(APIModel):
    service: str
    version: str
    docs: str
    health: str


class LiveHealthResponse(APIModel):
    status: Literal["ok"]
    service: str
    version: str


class ReadyHealthResponse(APIModel):
    status: Literal["ready"]
    database: str
    database_user: str
    postgis_version: str


class SnapshotResponse(APIModel):
    neighborhoods: int
    parks: int
    active_schools: int
    schools_in_scope: int
    open_park_features: int
    registered_sources: int
    successful_ingestion_runs: int


class NeighborhoodListItem(APIModel):
    neighborhood_id: str
    neighborhood_name: str
    active_school_count: int
    open_park_feature_count: int


class NeighborhoodListResponse(APIModel):
    items: list[NeighborhoodListItem]
    total: int
    limit: int
    offset: int


class NeighborhoodSummaryResponse(APIModel):
    neighborhood_id: str
    neighborhood_name: str
    active_school_count: int
    open_park_feature_count: int
    area_sq_km: Decimal


class SchoolNearParkItem(APIModel):
    cds_code: str
    school_name: str
    district_name: str
    education_level_code: str | None = None
    education_level_name: str | None = None
    neighborhood_id: str
    neighborhood_name: str
    nearest_open_park_id: str
    nearest_open_park_name: str
    park_type_code: str
    park_class_code: str
    distance_meters: Decimal
    distance_miles: Decimal


class SchoolNearParkResponse(APIModel):
    items: list[SchoolNearParkItem]
    total: int
    limit: int
    offset: int
    requested_distance_miles: float = Field(gt=0)
    education_level_code: str | None = None


class ParkSummary(APIModel):
    facility_id: str
    park_name: str
    park_type_code: str
    park_class_code: str
    current_status: str


class NearbySchoolItem(APIModel):
    cds_code: str
    school_name: str
    district_name: str
    education_level_code: str | None = None
    education_level_name: str | None = None
    neighborhood_id: str
    neighborhood_name: str
    distance_meters: Decimal
    distance_miles: Decimal


class ParkNearbySchoolsResponse(APIModel):
    park: ParkSummary
    distance_miles: float
    items: list[NearbySchoolItem]
    total: int
    limit: int
    offset: int
