"""Typed contracts for deterministic, non-executable SQL generation."""

from enum import Enum
from typing import Literal

from pydantic import Field, model_validator

from app.models.api import APIModel
from app.models.copilot import PlannerIntent, QueryPlan, QueryType


class SQLGenerationStatus(str, Enum):
    generated = "generated"
    blocked = "blocked"
    requires_clarification = "requires_clarification"


class SQLParameter(APIModel):
    position: int = Field(ge=1)
    name: str
    value: str | int | float | bool
    pg_type: Literal["text", "integer", "double precision", "boolean"]


class SQLSafetyCheck(APIModel):
    name: str
    passed: bool
    detail: str


class SQLGenerationRequest(APIModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=6, ge=1, le=10)


class SQLGenerationResponse(APIModel):
    generator: Literal["template_sql_day7"]
    planner: Literal["rule_based_day6"]
    question: str
    intent: PlannerIntent
    query_type: QueryType
    status: SQLGenerationStatus
    plan: QueryPlan
    sql: str | None = None
    statement_type: Literal["SELECT", "WITH", "NONE"]
    parameters: list[SQLParameter] = Field(default_factory=list)
    relations: list[str] = Field(default_factory=list)
    source_columns: list[str] = Field(default_factory=list)
    safety_checks: list[SQLSafetyCheck] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    execution_allowed: Literal[False] = False
    sql_generated: bool

    @model_validator(mode="after")
    def validate_generation_contract(self) -> "SQLGenerationResponse":
        if self.status == SQLGenerationStatus.generated:
            if not self.sql or not self.sql_generated:
                raise ValueError("generated status requires SQL")
            if self.statement_type == "NONE":
                raise ValueError("generated SQL requires a statement type")
        else:
            if self.sql is not None or self.sql_generated:
                raise ValueError("blocked generation must not expose SQL")
            if self.parameters:
                raise ValueError("blocked generation must not expose parameters")
        return self
