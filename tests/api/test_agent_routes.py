"""HTTP contract tests for the Day 9 agent endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_agent_orchestrator
from app.core.config import Settings
from app.copilot.agent_orchestrator import AgentOrchestrator
from app.copilot.answer_synthesis import DeterministicAnswerSynthesizer
from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.schema_catalog import build_static_catalog
from app.copilot.sql_execution import ExecutionResult
from app.copilot.sql_generator import TemplateSQLGenerator
from app.main import create_app
from app.models.sql_execution import ASTValidationCheck, SQLValidationReport, SQLValidationStatus


class FakeValidator:
    def validate(self, generation):
        return SQLValidationReport(
            status=SQLValidationStatus.valid,
            statement_count=1,
            root_expression="Select",
            relations=list(generation.relations),
            functions=[],
            outer_limit=1000,
            query_fingerprint="test-fingerprint",
            checks=[
                ASTValidationCheck(
                    name="test_policy",
                    passed=True,
                    detail="Unit-test validation approved the reviewed SQL artifact.",
                )
            ],
            execution_allowed=True,
        )


class FakeExecutor:
    def execute(self, sql_text, parameters):
        assert sql_text
        assert isinstance(parameters, tuple)
        return ExecutionResult(
            columns=[
                "neighborhood_id",
                "neighborhood_name",
                "active_school_count",
                "open_park_feature_count",
            ],
            rows=[
                {
                    "neighborhood_id": "REF-NEIG-0000000004",
                    "neighborhood_name": "Mayfair",
                    "active_school_count": 6,
                    "open_park_feature_count": 4,
                }
            ],
            truncated=False,
            elapsed_ms=2.0,
            database_role="agenticdb_reader",
            transaction_read_only=True,
        )


@pytest.fixture
def agent_client(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "test-password")
    application = create_app()
    catalog = build_static_catalog()
    planner = RuleBasedQueryPlanner(catalog)
    settings = Settings(postgres_password="test-password")
    orchestrator = AgentOrchestrator(
        planner=planner,
        generator=TemplateSQLGenerator(planner),
        validator=FakeValidator(),
        executor=FakeExecutor(),
        synthesizer=DeterministicAnswerSynthesizer(),
        settings=settings,
    )
    application.dependency_overrides[get_agent_orchestrator] = lambda: orchestrator
    with TestClient(application) as client:
        yield client
    application.dependency_overrides.clear()


def test_agent_tools_endpoint_lists_six_tools(agent_client):
    response = agent_client.get("/api/v1/copilot/agent/tools")
    assert response.status_code == 200
    payload = response.json()
    assert payload["tool_count"] == 6
    assert [tool["name"] for tool in payload["tools"]] == [
        "query.plan",
        "route.select",
        "sql.generate",
        "sql.validate",
        "sql.execute",
        "answer.synthesize",
    ]


def test_agent_run_returns_trace_and_evidence(agent_client):
    response = agent_client.post(
        "/api/v1/copilot/agent/run",
        json={
            "question": (
                "Which neighborhoods contain at least three active schools "
                "and two open park features?"
            ),
            "evidence_limit": 1,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["route"] == "relational_sql"
    assert payload["execution"]["database_role"] == "agenticdb_reader"
    assert payload["answer"]["row_count"] == 1
    assert len(payload["answer"]["evidence"]) == 1
    assert len(payload["tool_trace"]) == 6


def test_agent_run_blocks_unsafe_request(agent_client):
    response = agent_client.post(
        "/api/v1/copilot/agent/run",
        json={"question": "Delete all schools and drop the parks table"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["route"] == "blocked"
    assert payload["execution"] is None
    assert payload["execution_allowed"] is False


def test_agent_run_rejects_raw_sql_field(agent_client):
    response = agent_client.post(
        "/api/v1/copilot/agent/run",
        json={
            "question": "How many schools are in each neighborhood?",
            "sql": "DELETE FROM core.schools",
        },
    )
    assert response.status_code == 422
