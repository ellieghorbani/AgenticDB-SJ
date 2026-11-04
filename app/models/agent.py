"""Typed contracts for the Day 9 agent orchestration workflow."""

from enum import Enum
from typing import Any, Literal

from pydantic import Field, model_validator

from app.models.api import APIModel
from app.models.copilot import PlannerIntent, QueryPlan, QueryType
from app.models.sql_execution import SQLValidationReport
from app.models.sql_generation import SQLGenerationResponse, SQLParameter


class AgentRoute(str, Enum):
    relational_sql = "relational_sql"
    blocked = "blocked"
    unsupported = "unsupported"
    requires_clarification = "requires_clarification"


class AgentRunStatus(str, Enum):
    completed = "completed"
    blocked = "blocked"
    requires_clarification = "requires_clarification"


class AgentToolName(str, Enum):
    query_plan = "query.plan"
    route_select = "route.select"
    sql_generate = "sql.generate"
    sql_validate = "sql.validate"
    sql_execute = "sql.execute"
    answer_synthesize = "answer.synthesize"


class ToolCallStatus(str, Enum):
    succeeded = "succeeded"
    blocked = "blocked"
    skipped = "skipped"


class AgentToolDescriptor(APIModel):
    name: AgentToolName
    stage: str
    description: str
    database_access: bool
    safety_boundary: str


class AgentToolCatalogResponse(APIModel):
    agent: Literal["deterministic_agent_day9"] = "deterministic_agent_day9"
    tool_count: int = Field(ge=0)
    tools: list[AgentToolDescriptor]


class AgentToolTrace(APIModel):
    sequence: int = Field(ge=1)
    tool: AgentToolName
    status: ToolCallStatus
    elapsed_ms: float = Field(ge=0)
    input_summary: dict[str, Any] = Field(default_factory=dict)
    output_summary: dict[str, Any] = Field(default_factory=dict)
    message: str


class AgentEvidenceRow(APIModel):
    row_number: int = Field(ge=1)
    values: dict[str, Any]


class AgentAnswer(APIModel):
    text: str
    row_count: int = Field(ge=0)
    evidence: list[AgentEvidenceRow] = Field(default_factory=list)
    evidence_limited: bool = False
    sources: list[str] = Field(default_factory=list)
    query_fingerprint: str | None = None


class AgentExecutionSummary(APIModel):
    row_count: int = Field(ge=0)
    columns: list[str] = Field(default_factory=list)
    truncated: bool = False
    elapsed_ms: float = Field(ge=0)
    database_role: str
    transaction_read_only: bool
    statement_timeout_ms: int = Field(ge=0)
    query_fingerprint: str


class AgentRunRequest(APIModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=6, ge=1, le=10)
    evidence_limit: int = Field(default=5, ge=0, le=20)


class AgentRunResponse(APIModel):
    agent: Literal["deterministic_agent_day9"] = "deterministic_agent_day9"
    run_id: str
    status: AgentRunStatus
    route: AgentRoute
    question: str
    intent: PlannerIntent
    query_type: QueryType
    plan: QueryPlan
    generation: SQLGenerationResponse | None = None
    validation: SQLValidationReport | None = None
    execution: AgentExecutionSummary | None = None
    answer: AgentAnswer
    tool_trace: list[AgentToolTrace]
    warnings: list[str] = Field(default_factory=list)
    total_elapsed_ms: float = Field(ge=0)
    execution_allowed: bool = False

    @model_validator(mode="after")
    def validate_agent_contract(self) -> "AgentRunResponse":
        expected_sequence = list(range(1, len(self.tool_trace) + 1))
        actual_sequence = [trace.sequence for trace in self.tool_trace]
        if actual_sequence != expected_sequence:
            raise ValueError("tool trace sequence must be contiguous and ordered")

        if self.status == AgentRunStatus.completed:
            if self.route != AgentRoute.relational_sql:
                raise ValueError("completed runs require the relational_sql route")
            if self.execution is None or not self.execution_allowed:
                raise ValueError("completed runs require an allowed execution summary")
            if not self.execution.transaction_read_only:
                raise ValueError("completed runs require a read-only transaction")
            if self.answer.row_count != self.execution.row_count:
                raise ValueError("answer and execution row counts must agree")
        else:
            if self.execution is not None or self.execution_allowed:
                raise ValueError("blocked or unresolved runs cannot include execution")
            if self.answer.row_count != 0:
                raise ValueError("non-completed runs cannot claim database rows")
        return self
