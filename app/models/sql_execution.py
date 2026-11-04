"""Typed contracts for Day 8 SQL AST validation and controlled execution."""

from enum import Enum
from typing import Any, Literal

from pydantic import Field, model_validator

from app.models.api import APIModel
from app.models.sql_generation import SQLGenerationResponse


class SQLValidationStatus(str, Enum):
    valid = "valid"
    blocked = "blocked"
    not_generated = "not_generated"


class SQLExecutionStatus(str, Enum):
    executed = "executed"
    blocked = "blocked"


class ASTValidationCheck(APIModel):
    name: str
    passed: bool
    detail: str


class SQLValidationReport(APIModel):
    validator: Literal["sqlglot_ast_day8"] = "sqlglot_ast_day8"
    dialect: Literal["postgres"] = "postgres"
    status: SQLValidationStatus
    statement_count: int = Field(ge=0)
    root_expression: str | None = None
    relations: list[str] = Field(default_factory=list)
    functions: list[str] = Field(default_factory=list)
    outer_limit: int | None = Field(default=None, ge=0)
    query_fingerprint: str | None = None
    checks: list[ASTValidationCheck] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    execution_allowed: bool = False

    @model_validator(mode="after")
    def validate_execution_contract(self) -> "SQLValidationReport":
        all_passed = bool(self.checks) and all(check.passed for check in self.checks)
        if self.execution_allowed and (
            self.status != SQLValidationStatus.valid or not all_passed
        ):
            raise ValueError(
                "execution can be allowed only for a valid report with all checks passing"
            )
        return self


class SQLValidationRequest(APIModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=6, ge=1, le=10)


class SQLValidationResponse(APIModel):
    generation: SQLGenerationResponse
    validation: SQLValidationReport


class SQLExecutionRequest(APIModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=6, ge=1, le=10)


class SQLExecutionResponse(APIModel):
    executor: Literal["psycopg_readonly_day8"] = "psycopg_readonly_day8"
    status: SQLExecutionStatus
    generation: SQLGenerationResponse
    validation: SQLValidationReport
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = Field(default=0, ge=0)
    truncated: bool = False
    elapsed_ms: float | None = Field(default=None, ge=0)
    database_role: str | None = None
    transaction_read_only: bool = False
    statement_timeout_ms: int | None = Field(default=None, ge=0)
    warnings: list[str] = Field(default_factory=list)
    execution_allowed: bool = False

    @model_validator(mode="after")
    def validate_execution_response(self) -> "SQLExecutionResponse":
        if self.status == SQLExecutionStatus.executed:
            if not self.execution_allowed:
                raise ValueError("executed responses must indicate execution was allowed")
            if not self.transaction_read_only:
                raise ValueError("executed responses require a read-only transaction")
            if self.validation.execution_allowed is not True:
                raise ValueError("execution requires an approved validation report")
        else:
            if self.rows or self.columns or self.row_count:
                raise ValueError("blocked responses cannot contain database rows")
            if self.execution_allowed:
                raise ValueError("blocked responses cannot allow execution")
        return self
