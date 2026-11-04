"""Unit tests for Day 8 execution orchestration."""

from app.core.config import Settings
from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.schema_catalog import build_static_catalog
from app.copilot.sql_execution import CopilotExecutionService, ExecutionResult
from app.copilot.sql_generator import TemplateSQLGenerator
from app.copilot.sql_validator import SQLASTValidator


class FakeExecutor:
    def __init__(self):
        self.calls = 0

    def execute(self, sql_text, parameters):
        self.calls += 1
        assert sql_text
        assert parameters == (3, 2)
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
            elapsed_ms=1.25,
            database_role="agenticdb_reader",
            transaction_read_only=True,
        )


def build_service():
    catalog = build_static_catalog()
    generator = TemplateSQLGenerator(RuleBasedQueryPlanner(catalog))
    validator = SQLASTValidator(catalog, max_result_rows=1000)
    executor = FakeExecutor()
    settings = Settings(postgres_password="test-password")
    return (
        CopilotExecutionService(generator, validator, executor, settings),
        executor,
    )


def test_valid_question_executes_after_ast_validation():
    service, executor = build_service()
    response = service.execute(
        "Which neighborhoods contain at least three active schools and two open parks?"
    )
    assert response.status.value == "executed"
    assert response.execution_allowed is True
    assert response.validation.execution_allowed is True
    assert response.database_role == "agenticdb_reader"
    assert response.transaction_read_only is True
    assert response.row_count == 1
    assert executor.calls == 1


def test_unsafe_question_never_calls_executor():
    service, executor = build_service()
    response = service.execute("Delete all school records")
    assert response.status.value == "blocked"
    assert response.execution_allowed is False
    assert response.row_count == 0
    assert executor.calls == 0
