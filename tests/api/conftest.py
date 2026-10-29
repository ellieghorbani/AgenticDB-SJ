"""Unit-test fixtures that replace the database service."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_query_service
from app.core.errors import ResourceNotFoundError
from app.main import create_app


class FakeQueryService:
    def readiness(self):
        return {
            "status": "ready",
            "database": "agenticdb_sj",
            "database_user": "agenticdb_api",
            "postgis_version": "3.5-test",
        }

    def snapshot(self):
        return {
            "neighborhoods": 297,
            "parks": 611,
            "active_schools": 10537,
            "schools_in_scope": 220,
            "open_park_features": 526,
            "registered_sources": 3,
            "successful_ingestion_runs": 3,
        }

    def list_neighborhoods(
        self,
        *,
        min_schools,
        min_open_park_features,
        limit,
        offset,
    ):
        del min_schools, min_open_park_features
        items = [
            {
                "neighborhood_id": "REF-NEIG-0000000004",
                "neighborhood_name": "Mayfair",
                "active_school_count": 6,
                "open_park_feature_count": 4,
            }
        ]
        return items[:limit], 1 if offset == 0 else 0

    def neighborhood_summary(self, neighborhood_id):
        if neighborhood_id == "missing":
            raise ResourceNotFoundError("Neighborhood 'missing' was not found.")
        return {
            "neighborhood_id": neighborhood_id,
            "neighborhood_name": "Mayfair",
            "active_school_count": 6,
            "open_park_feature_count": 4,
            "area_sq_km": Decimal("1.2345"),
        }

    def schools_near_open_parks(
        self,
        *,
        distance_miles,
        education_level_code,
        limit,
        offset,
    ):
        del distance_miles, education_level_code, limit, offset
        return [
            {
                "cds_code": "12345678901234",
                "school_name": "Example Elementary",
                "district_name": "Example District",
                "education_level_code": "ELEM",
                "education_level_name": "Elementary",
                "neighborhood_id": "REF-NEIG-0000000004",
                "neighborhood_name": "Mayfair",
                "nearest_open_park_id": "788",
                "nearest_open_park_name": "Example Park",
                "park_type_code": "NBR",
                "park_class_code": "PARK",
                "distance_meters": Decimal("250.00"),
                "distance_miles": Decimal("0.1553"),
            }
        ], 1

    def park_nearby_schools(
        self,
        *,
        facility_id,
        distance_miles,
        limit,
        offset,
    ):
        if facility_id == "missing":
            raise ResourceNotFoundError("Park 'missing' was not found.")
        return {
            "park": {
                "facility_id": facility_id,
                "park_name": "Example Park",
                "park_type_code": "NBR",
                "park_class_code": "PARK",
                "current_status": "Open",
            },
            "distance_miles": distance_miles,
            "items": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
        }


@pytest.fixture
def client():
    application = create_app()
    fake_service = FakeQueryService()
    application.dependency_overrides[get_query_service] = lambda: fake_service
    with TestClient(application) as test_client:
        yield test_client
    application.dependency_overrides.clear()
