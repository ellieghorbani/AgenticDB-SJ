"""HTTP contract tests for Day 11 hosted-planning endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_llm_agent_orchestrator,
    get_llm_planning_service,
)
from app.core.config import Settings, get_settings
from app.copilot.answer_synthesis import DeterministicAnswerSynthesizer
from app.copilot.llm_orchestrator import LLMAssistedAgentOrchestrator
from app.copilot.llm_planner import LLMAssistedPlanningService
from app.copilot.llm_provider import PlanningProviderResult
from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.schema_catalog import build_static_catalog
from app.copilot.sql_execution import ExecutionResult
from app.copilot.sql_generator import TemplateSQLGenerator
from app.main import create_app
from app.models.copilot import PlannerIntent
from app.models.llm import LLMPlanProposal, ModelUsage
from app.models.sql_execution import (
    ASTValidationCheck,
    SQLValidationReport,
    SQLValidationStatus,
)


class FakeProvider:
    provider_name = "fake_openai"
    model = "fake-model"

    def propose(self, question, schema_summary):
        del question, schema_summary
        return PlanningProviderResult(
            proposal=LLMPlanProposal(
                intent=PlannerIntent.neighborhoods_with_minimum_schools_and_parks,
                confidence=0.99,
                minimum_school_count=3,
                minimum_park_count=2,
                distance_value=None,
                distance_unit=None,
                neighborhood_name=None,
                requires_clarification=False,
                clarification_question=None,
                rationale="Two independent thresholds were requested.",
            ),
            usage=ModelUsage(
                api_called=True,
                response_id="resp_api_test",
                model=self.model,
                input_tokens=50,
                output_tokens=10,
                total_tokens=60,
                elapsed_ms=2.0,
            ),
        )


class FakeValidator:
    def validate(self, generation):
        return SQLValidationReport(
            status=SQLValidationStatus.valid,
            statement_count=1,
            root_expression="Select",
            relations=list(generation.relations),
            functions=[],
            outer_limit=1000,
            query_fingerprint="llm-test-fingerprint",
            checks=[
                ASTValidationCheck(
                    name="test_policy",
                    passed=True,
                    detail="Approved in the route unit test.",
                )
            ],
            execution_allowed=True,
        )


class FakeExecutor:
    def execute(self, sql_text, parameters):
        assert sql_text
        assert parameters == (3, 2)
        rows = [
            {
                "neighborhood_id": "REF-NEIG-0000000004",
                "neighborhood_name": "Mayfair",
                "active_school_count": 6,
                "open_park_feature_count": 6,
            }
        ]
        return ExecutionResult(
            columns=list(rows[0]),
            rows=rows,
            truncated=False,
            elapsed_ms=1.0,
            database_role="agenticdb_reader",
            transaction_read_only=True,
        )


@pytest.fixture
def llm_client(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "test-password")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("PLANNING_PROVIDER", "openai")
    get_settings.cache_clear()

    catalog = build_static_catalog()
    deterministic = RuleBasedQueryPlanner(catalog)
    service = LLMAssistedPlanningService(
        deterministic,
        catalog,
        provider=FakeProvider(),
        default_provider="openai",
        fallback_to_deterministic=False,
    )
    settings = Settings(
        postgres_password="test-password",
        openai_api_key="test-key",
        planning_provider="openai",
    )
    orchestrator = LLMAssistedAgentOrchestrator(
        planning_service=service,
        generator=TemplateSQLGenerator(deterministic),
        validator=FakeValidator(),
        executor=FakeExecutor(),
        synthesizer=DeterministicAnswerSynthesizer(),
        settings=settings,
    )

    application = create_app()
    application.dependency_overrides[get_llm_planning_service] = lambda: service
    application.dependency_overrides[get_llm_agent_orchestrator] = lambda: orchestrator
    with TestClient(application) as client:
        yield client
    application.dependency_overrides.clear()
    get_settings.cache_clear()


def test_llm_status(llm_client):
    response = llm_client.get("/api/v1/copilot/llm/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["planning_provider"] == "openai"
    assert payload["openai_api_key_configured"] is True


def test_llm_plan_returns_typed_plan_and_usage(llm_client):
    response = llm_client.post(
        "/api/v1/copilot/llm/plan",
        json={
            "question": "Find areas with three schools and two parks.",
            "provider": "openai",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_used"] == "openai"
    assert payload["plan"]["intent"] == "neighborhoods_with_minimum_schools_and_parks"
    assert payload["usage"]["total_tokens"] == 60
    assert payload["plan"]["execution_allowed"] is False


def test_llm_run_preserves_existing_safety_chain(llm_client):
    response = llm_client.post(
        "/api/v1/copilot/llm/run",
        json={
            "question": "Find areas with three schools and two parks.",
            "provider": "openai",
            "evidence_limit": 1,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["planning"]["provider_used"] == "openai"
    assert payload["run"]["status"] == "completed"
    assert payload["run"]["execution"]["database_role"] == "agenticdb_reader"
    assert payload["run"]["execution"]["transaction_read_only"] is True
    assert payload["run"]["answer"]["row_count"] == 1


def test_llm_run_rejects_raw_sql(llm_client):
    response = llm_client.post(
        "/api/v1/copilot/llm/run",
        json={
            "question": "Find areas with three schools and two parks.",
            "provider": "openai",
            "sql": "DELETE FROM core.schools",
        },
    )
    assert response.status_code == 422
