"""Unit tests for the Day 9 traced agent workflow."""

from app.core.config import Settings
from app.copilot.agent_orchestrator import AgentOrchestrator
from app.copilot.answer_synthesis import DeterministicAnswerSynthesizer
from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.schema_catalog import build_static_catalog
from app.copilot.sql_execution import ExecutionResult
from app.copilot.sql_generator import TemplateSQLGenerator
from app.models.agent import AgentRoute, AgentRunStatus, AgentToolName, ToolCallStatus
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
    def __init__(self, rows):
        self.rows = rows
        self.calls = 0

    def execute(self, sql_text, parameters):
        self.calls += 1
        assert sql_text
        assert isinstance(parameters, tuple)
        columns = list(self.rows[0]) if self.rows else []
        return ExecutionResult(
            columns=columns,
            rows=list(self.rows),
            truncated=False,
            elapsed_ms=1.5,
            database_role="agenticdb_reader",
            transaction_read_only=True,
        )


def build_orchestrator(rows):
    catalog = build_static_catalog()
    planner = RuleBasedQueryPlanner(catalog)
    generator = TemplateSQLGenerator(planner)
    validator = FakeValidator()
    executor = FakeExecutor(rows)
    settings = Settings(postgres_password="test-password")
    return (
        AgentOrchestrator(
            planner=planner,
            generator=generator,
            validator=validator,
            executor=executor,
            synthesizer=DeterministicAnswerSynthesizer(),
            settings=settings,
        ),
        executor,
    )


def test_supported_question_runs_all_tools_and_returns_evidence():
    orchestrator, executor = build_orchestrator(
        [
            {
                "neighborhood_id": "REF-NEIG-0000000004",
                "neighborhood_name": "Mayfair",
                "active_school_count": 6,
                "open_park_feature_count": 4,
            }
        ]
    )
    response = orchestrator.run(
        "Which neighborhoods contain at least three active schools and two open parks?",
        evidence_limit=1,
    )

    assert response.status == AgentRunStatus.completed
    assert response.route == AgentRoute.relational_sql
    assert response.execution_allowed is True
    assert response.execution is not None
    assert response.execution.database_role == "agenticdb_reader"
    assert response.answer.row_count == 1
    assert len(response.answer.evidence) == 1
    assert executor.calls == 1
    assert [item.tool for item in response.tool_trace] == list(AgentToolName)
    assert all(item.status == ToolCallStatus.succeeded for item in response.tool_trace)


def test_unsafe_request_stops_before_generation_and_execution():
    orchestrator, executor = build_orchestrator([])
    response = orchestrator.run("Delete all schools and drop the parks table")

    assert response.status == AgentRunStatus.blocked
    assert response.route == AgentRoute.blocked
    assert response.execution is None
    assert executor.calls == 0
    statuses = [item.status for item in response.tool_trace]
    assert statuses == [
        ToolCallStatus.succeeded,
        ToolCallStatus.blocked,
        ToolCallStatus.skipped,
        ToolCallStatus.skipped,
        ToolCallStatus.skipped,
        ToolCallStatus.succeeded,
    ]


def test_unsupported_request_stops_without_database_contact():
    orchestrator, executor = build_orchestrator([])
    response = orchestrator.run("Find family-friendly concerts this weekend")

    assert response.status == AgentRunStatus.blocked
    assert response.route == AgentRoute.unsupported
    assert executor.calls == 0
    assert response.answer.row_count == 0


def test_ambiguous_request_requires_clarification():
    orchestrator, executor = build_orchestrator([])
    response = orchestrator.run("Which open park features intersect neighborhoods?")

    assert response.status == AgentRunStatus.requires_clarification
    assert response.route == AgentRoute.requires_clarification
    assert executor.calls == 0
    assert "clarification" in response.answer.text.lower()


def test_zero_row_execution_is_completed_without_invented_evidence():
    orchestrator, executor = build_orchestrator([])
    response = orchestrator.run(
        "Which active schools have no open park feature within one mile?"
    )

    assert response.status == AgentRunStatus.completed
    assert response.answer.row_count == 0
    assert response.answer.evidence == []
    assert response.answer.text == "No database rows matched the validated query."
    assert executor.calls == 1
