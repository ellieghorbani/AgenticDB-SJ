"""Day 8 validation orchestration and controlled read-only SQL execution."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from psycopg import Connection
from psycopg import sql as psycopg_sql

from app.core.config import Settings
from app.copilot.sql_generator import TemplateSQLGenerator
from app.copilot.sql_validator import SQLASTValidator
from app.models.sql_execution import (
    SQLExecutionResponse,
    SQLExecutionStatus,
    SQLValidationResponse,
)


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    columns: list[str]
    rows: list[dict[str, Any]]
    truncated: bool
    elapsed_ms: float
    database_role: str
    transaction_read_only: bool


class ReadOnlySQLExecutor:
    """Execute only independently validated SQL under a restricted DB role."""

    executor_name = "psycopg_readonly_day8"

    def __init__(self, connection: Connection, settings: Settings):
        self.connection = connection
        self.settings = settings

    def execute(self, sql_text: str, parameters: tuple[Any, ...]) -> ExecutionResult:
        with self.connection.cursor() as cursor:
            cursor.execute(
                psycopg_sql.SQL("SET LOCAL ROLE {}").format(
                    psycopg_sql.Identifier(self.settings.copilot_execution_role)
                )
            )
            cursor.execute(
                "SELECT set_config('statement_timeout', %s, true)",
                (str(self.settings.copilot_execution_timeout_ms),),
            )
            cursor.execute(
                "SELECT set_config('lock_timeout', %s, true)",
                (str(self.settings.copilot_lock_timeout_ms),),
            )
            cursor.execute(
                """
                SELECT
                    current_setting('transaction_read_only') = 'on'
                        AS transaction_read_only,
                    current_user AS database_role
                """
            )
            state = cursor.fetchone()
            assert state is not None
            transaction_read_only = bool(state["transaction_read_only"])
            database_role = str(state["database_role"])
            if not transaction_read_only:
                raise RuntimeError("controlled execution requires a read-only transaction")
            if database_role != self.settings.copilot_execution_role:
                raise RuntimeError(
                    "controlled execution did not assume the configured restricted role"
                )

            started = perf_counter()
            cursor.execute(sql_text, parameters)
            columns = (
                [description.name for description in cursor.description]
                if cursor.description is not None
                else []
            )
            fetched = cursor.fetchmany(self.settings.copilot_max_result_rows + 1)
            elapsed_ms = (perf_counter() - started) * 1000.0

        truncated = len(fetched) > self.settings.copilot_max_result_rows
        selected = fetched[: self.settings.copilot_max_result_rows]
        rows = [dict(row) for row in selected]
        return ExecutionResult(
            columns=columns,
            rows=rows,
            truncated=truncated,
            elapsed_ms=round(elapsed_ms, 3),
            database_role=database_role,
            transaction_read_only=transaction_read_only,
        )


class SQLValidationService:
    """Generate SQL and return the independent AST-validation report."""

    def __init__(
        self,
        generator: TemplateSQLGenerator,
        validator: SQLASTValidator,
    ):
        self.generator = generator
        self.validator = validator

    def validate(self, question: str, *, top_k: int = 6) -> SQLValidationResponse:
        generation = self.generator.generate(question, top_k=top_k)
        validation = self.validator.validate(generation)
        return SQLValidationResponse(
            generation=generation,
            validation=validation,
        )


class CopilotExecutionService:
    """Generate, validate, and conditionally execute one supported question."""

    def __init__(
        self,
        generator: TemplateSQLGenerator,
        validator: SQLASTValidator,
        executor: ReadOnlySQLExecutor,
        settings: Settings,
    ):
        self.generator = generator
        self.validator = validator
        self.executor = executor
        self.settings = settings

    def execute(self, question: str, *, top_k: int = 6) -> SQLExecutionResponse:
        generation = self.generator.generate(question, top_k=top_k)
        validation = self.validator.validate(generation)

        if not validation.execution_allowed or generation.sql is None:
            return SQLExecutionResponse(
                status=SQLExecutionStatus.blocked,
                generation=generation,
                validation=validation,
                warnings=[
                    *generation.warnings,
                    *validation.warnings,
                    "The database was not contacted because validation did not grant execution.",
                ],
                execution_allowed=False,
            )

        parameters = tuple(parameter.value for parameter in generation.parameters)
        result = self.executor.execute(generation.sql, parameters)
        warnings = list(validation.warnings)
        if result.truncated:
            warnings.append(
                f"Results were truncated to {self.settings.copilot_max_result_rows} rows."
            )

        return SQLExecutionResponse(
            status=SQLExecutionStatus.executed,
            generation=generation,
            validation=validation,
            columns=result.columns,
            rows=result.rows,
            row_count=len(result.rows),
            truncated=result.truncated,
            elapsed_ms=result.elapsed_ms,
            database_role=result.database_role,
            transaction_read_only=result.transaction_read_only,
            statement_timeout_ms=self.settings.copilot_execution_timeout_ms,
            warnings=warnings,
            execution_allowed=True,
        )
