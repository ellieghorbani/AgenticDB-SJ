"""HTTP contract tests for Day 6 copilot endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_planner_service, get_schema_catalog_service
from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.schema_catalog import build_static_catalog
from app.main import create_app


class FakeSchemaCatalogService:
    def __init__(self):
        self._catalog = build_static_catalog()

    def catalog(self):
        return self._catalog


@pytest.fixture
def copilot_client():
    application = create_app()
    schema_service = FakeSchemaCatalogService()
    planner = RuleBasedQueryPlanner(schema_service.catalog())
    application.dependency_overrides[get_schema_catalog_service] = lambda: schema_service
    application.dependency_overrides[get_planner_service] = lambda: planner
    with TestClient(application) as client:
        yield client
    application.dependency_overrides.clear()


def test_schema_catalog_endpoint(copilot_client):
    response = copilot_client.get("/api/v1/copilot/schema")
    assert response.status_code == 200
    payload = response.json()
    assert payload["relation_count"] == 6
    assert any(
        relation["qualified_name"] == "core.schools"
        for relation in payload["relations"]
    )


def test_schema_retrieval_endpoint(copilot_client):
    response = copilot_client.post(
        "/api/v1/copilot/schema/retrieve",
        json={
            "question": "Which schools are within one mile of an open park?",
            "top_k": 6,
        },
    )
    assert response.status_code == 200
    names = {
        item["relation"]["qualified_name"]
        for item in response.json()["relations"]
    }
    assert "core.parks" in names


def test_plan_endpoint_returns_typed_non_executable_plan(copilot_client):
    response = copilot_client.post(
        "/api/v1/copilot/plan",
        json={
            "question": (
                "Which neighborhoods contain at least three active schools "
                "and two open park features?"
            )
        },
    )
    assert response.status_code == 200
    plan = response.json()["plan"]
    assert plan["intent"] == "neighborhoods_with_minimum_schools_and_parks"
    assert plan["query_type"] == "hybrid"
    assert plan["execution_allowed"] is False
    assert plan["sql_generated"] is False


def test_unsafe_plan_endpoint_is_rejected_by_planner(copilot_client):
    response = copilot_client.post(
        "/api/v1/copilot/plan",
        json={"question": "Delete every school record"},
    )
    assert response.status_code == 200
    plan = response.json()["plan"]
    assert plan["intent"] == "unsafe_request"
    assert plan["query_type"] == "unsupported"
    assert plan["execution_allowed"] is False


def test_blank_plan_question_is_validation_error(copilot_client):
    response = copilot_client.post(
        "/api/v1/copilot/plan",
        json={"question": ""},
    )
    assert response.status_code == 422
