"""Typed contracts for Day 11 hosted LLM and embedding providers."""

from enum import Enum
from typing import Literal

from pydantic import Field, model_validator

from app.models.agent import AgentRunResponse
from app.models.api import APIModel
from app.models.copilot import PlannerIntent, QueryPlan, SchemaContextResponse


class RequestedPlanningProvider(str, Enum):
    default = "default"
    deterministic = "deterministic"
    openai = "openai"


class LLMPlanProposal(APIModel):
    """Strict structured output returned by the hosted planning model."""

    intent: PlannerIntent
    confidence: float = Field(ge=0, le=1)
    minimum_school_count: int | None = Field(ge=0, le=1000)
    minimum_park_count: int | None = Field(ge=0, le=1000)
    distance_value: float | None = Field(gt=0, le=1000)
    distance_unit: Literal["miles", "kilometers"] | None
    neighborhood_name: str | None = Field(max_length=200)
    requires_clarification: bool
    clarification_question: str | None = Field(max_length=500)
    rationale: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_proposal(self) -> "LLMPlanProposal":
        if self.requires_clarification and not self.clarification_question:
            raise ValueError(
                "clarification_question is required when clarification is requested"
            )
        return self


class ModelUsage(APIModel):
    api_called: bool = False
    response_id: str | None = None
    model: str | None = None
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    elapsed_ms: float = Field(default=0.0, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)


class LLMProviderStatusResponse(APIModel):
    status: Literal["ready", "configuration_required"]
    planning_provider: Literal["deterministic", "openai"]
    openai_api_key_configured: bool
    openai_llm_model: str
    deterministic_fallback_enabled: bool
    embedding_provider: Literal["local", "openai"]
    active_embedding_model: str
    active_embedding_dimensions: int


class LLMPlanRequest(APIModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=6, ge=1, le=10)
    provider: RequestedPlanningProvider = RequestedPlanningProvider.default


class LLMPlanResponse(APIModel):
    planner: str
    provider_requested: RequestedPlanningProvider
    provider_used: Literal[
        "deterministic",
        "openai",
        "deterministic_fallback",
        "local_safety_gate",
    ]
    fallback_used: bool = False
    model: str | None = None
    proposal: LLMPlanProposal | None = None
    plan: QueryPlan
    schema_context: SchemaContextResponse
    usage: ModelUsage
    warnings: list[str] = Field(default_factory=list)


class LLMAgentRunRequest(LLMPlanRequest):
    evidence_limit: int = Field(default=5, ge=0, le=20)


class LLMAgentRunResponse(APIModel):
    agent: Literal["openai_assisted_agent_day11"] = "openai_assisted_agent_day11"
    planning: LLMPlanResponse
    run: AgentRunResponse
    total_elapsed_ms: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_run(self) -> "LLMAgentRunResponse":
        if self.planning.plan.intent != self.run.intent:
            raise ValueError("planning and execution intents must agree")
        if self.planning.plan.question != self.run.question:
            raise ValueError("planning and execution questions must agree")
        return self
