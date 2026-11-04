"""HTTP contract tests for Day 8 validation and execution endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_copilot_execution_service,
    get_sql_validation_service,
)
from app.core.config import Settings
from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.schema_catalog import build_static_catalog
from app.copilot.sql_execution import (
    CopilotExecutionService,
    ExecutionResult,
    SQLValidationService,
)
from app.copilot.sql_generator import TemplateSQLGenerator
from app.copilot.sql_validator import SQLASTValidator
from app.main import create_app


class FakeExecutor:
    def execute(self, sql_text, parameters):
        assert sql_text
        assert isinstance(parameters, tuple)
        return ExecutionResult(
            columns=["neighborhood_id", "neighborhood_name"],
            rows=[
                {
                    "neighborhood_id": "REF-NEIG-0000000004",
                    "neighborhood_name": "Mayfair",
                }
            ],
            truncated=False,
            elapsed_ms=2.5,
            database_role="agenticdb_reader",
            transaction_read_only=True,
        )


@pytest.fixture
def day8_client():
    application = create_app()
    catalog = build_static_catalog()
    generator = TemplateSQLGenerator(RuleBasedQueryPlanner(catalog))
    validator = SQLASTValidator(catalog, max_result_rows=1000)
    settings = Settings(postgres_password="test-password")
    validation_service = SQLValidationService(generator, validator)
    execution_service = CopilotExecutionService(
        generator,
        validator,
        FakeExecutor(),
        settings,
    )
    application.dependency_overrides[get_sql_validation_service] = (
        lambda: validation_service
    )
    application.dependency_overrides[get_copilot_execution_service] = (
        lambda: execution_service
    )
    with TestClient(application) as client:
        yield client
    application.dependency_overrides.clear()


def test_validate_endpoint_approves_supported_query(day8_client):
    response = day8_client.post(
        "/api/v1/copilot/validate",
        json={
            "question": (
                "Which neighborhoods contain at least three active schools "
                "and two open park features?"
            )
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["validation"]["status"] == "valid"
    assert payload["validation"]["execution_allowed"] is True
    assert all(check["passed"] for check in payload["validation"]["checks"])


def test_execute_endpoint_returns_validated_rows(day8_client):
    response = day8_client.post(
        "/api/v1/copilot/execute",
        json={
            "question": (
                "Which neighborhoods contain at least three active schools "
                "and two open park features?"
            )
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "executed"
    assert payload["row_count"] == 1
    assert payload["database_role"] == "agenticdb_reader"
    assert payload["transaction_read_only"] is True


def test_execute_endpoint_blocks_unsafe_question(day8_client):
    response = day8_client.post(
        "/api/v1/copilot/execute",
        json={"question": "Delete all schools and drop the parks table"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["row_count"] == 0
    assert payload["execution_allowed"] is False


def test_execute_endpoint_rejects_raw_sql_field(day8_client):
    response = day8_client.post(
        "/api/v1/copilot/execute",
        json={
            "question": "How many schools are in each neighborhood?",
            "sql": "DELETE FROM core.schools",
        },
    )
    assert response.status_code == 422
