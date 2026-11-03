"""HTTP contract tests for the Day 7 SQL-generation endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_planner_service,
    get_schema_catalog_service,
    get_sql_generator_service,
)
from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.schema_catalog import build_static_catalog
from app.copilot.sql_generator import TemplateSQLGenerator
from app.main import create_app


class FakeSchemaCatalogService:
    def __init__(self):
        self._catalog = build_static_catalog()

    def catalog(self):
        return self._catalog


@pytest.fixture
def sql_client():
    application = create_app()
    schema_service = FakeSchemaCatalogService()
    planner = RuleBasedQueryPlanner(schema_service.catalog())
    generator = TemplateSQLGenerator(planner)
    application.dependency_overrides[get_schema_catalog_service] = lambda: schema_service
    application.dependency_overrides[get_planner_service] = lambda: planner
    application.dependency_overrides[get_sql_generator_service] = lambda: generator
    with TestClient(application) as client:
        yield client
    application.dependency_overrides.clear()


def test_sql_endpoint_generates_parameterized_query(sql_client):
    response = sql_client.post(
        "/api/v1/copilot/sql",
        json={
            "question": (
                "Which neighborhoods contain at least three active schools "
                "and two open park features?"
            )
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "generated"
    assert payload["statement_type"] == "WITH"
    assert payload["sql_generated"] is True
    assert payload["execution_allowed"] is False
    assert [item["value"] for item in payload["parameters"]] == [3, 2]
    assert all(item["passed"] for item in payload["safety_checks"])


def test_sql_endpoint_blocks_unsafe_request(sql_client):
    response = sql_client.post(
        "/api/v1/copilot/sql",
        json={"question": "Delete every school record"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["sql"] is None
    assert payload["sql_generated"] is False


def test_sql_endpoint_blocks_unsupported_request(sql_client):
    response = sql_client.post(
        "/api/v1/copilot/sql",
        json={"question": "Find family-friendly concerts this weekend"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"


def test_sql_endpoint_requires_question(sql_client):
    response = sql_client.post("/api/v1/copilot/sql", json={"question": ""})
    assert response.status_code == 422
