"""Typed contracts for Day 10 pgvector semantic and hybrid retrieval."""

from enum import Enum
from typing import Any, Literal

from pydantic import Field, model_validator

from app.models.api import APIModel


class VectorEntityType(str, Enum):
    park = "park"
    school = "school"
    neighborhood = "neighborhood"


class VectorRoute(str, Enum):
    semantic_vector = "semantic_vector"
    hybrid_vector = "hybrid_vector"
    blocked = "blocked"
    unsupported = "unsupported"


class VectorRunStatus(str, Enum):
    completed = "completed"
    blocked = "blocked"


class VectorRouteRequest(APIModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.20, ge=-1.0, le=1.0)


class VectorRouteDecision(APIModel):
    router: Literal["deterministic_vector_router_day10"] = (
        "deterministic_vector_router_day10"
    )
    question: str
    route: VectorRoute
    query_text: str
    entity_types: list[VectorEntityType] = Field(default_factory=list)
    only_open_parks: bool = False
    education_level_code: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.20, ge=-1.0, le=1.0)
    reason: str
    execution_allowed: bool = False

    @model_validator(mode="after")
    def validate_route(self) -> "VectorRouteDecision":
        if self.route in {VectorRoute.blocked, VectorRoute.unsupported}:
            if self.execution_allowed:
                raise ValueError("blocked and unsupported routes cannot execute")
        elif not self.entity_types:
            raise ValueError("vector routes require at least one entity type")
        return self


class VectorSearchRequest(APIModel):
    query: str = Field(min_length=3, max_length=1000)
    entity_types: list[VectorEntityType] = Field(
        default_factory=lambda: list(VectorEntityType)
    )
    top_k: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.20, ge=-1.0, le=1.0)
    only_open_parks: bool = False
    education_level_code: str | None = Field(
        default=None,
        pattern=r"^[A-Z0-9_-]{1,20}$",
    )

    @model_validator(mode="after")
    def validate_filters(self) -> "VectorSearchRequest":
        if not self.entity_types:
            raise ValueError("at least one entity type is required")
        if self.only_open_parks and VectorEntityType.park not in self.entity_types:
            raise ValueError("only_open_parks requires the park entity type")
        if (
            self.education_level_code is not None
            and VectorEntityType.school not in self.entity_types
        ):
            raise ValueError(
                "education_level_code requires the school entity type"
            )
        return self


class VectorMatch(APIModel):
    document_id: int
    entity_type: VectorEntityType
    entity_id: str
    title: str
    source_text: str
    similarity: float = Field(ge=-1.0, le=1.0)
    metadata: dict[str, Any]


class VectorSearchResponse(APIModel):
    provider: str = "sentence_transformers_pgvector_day10"
    model: str
    dimensions: int = Field(ge=1)
    query: str
    entity_types: list[VectorEntityType]
    only_open_parks: bool
    education_level_code: str | None = None
    top_k: int
    min_similarity: float
    match_count: int = Field(ge=0)
    matches: list[VectorMatch]
    elapsed_ms: float = Field(ge=0)
    database_role: str
    transaction_read_only: bool


class VectorStatusResponse(APIModel):
    status: Literal["ready"]
    provider: str = "sentence_transformers_pgvector_day10"
    extension_version: str
    document_count: int = Field(ge=0)
    embedded_document_count: int = Field(ge=0)
    embedding_model: str
    embedding_dimensions: int = Field(ge=1)
    entity_counts: dict[str, int]
    hnsw_index_present: bool


class VectorToolTrace(APIModel):
    sequence: int = Field(ge=1)
    tool: str
    status: Literal["succeeded", "blocked", "skipped"]
    elapsed_ms: float = Field(ge=0)
    message: str
    output_summary: dict[str, Any] = Field(default_factory=dict)


class VectorRunRequest(VectorRouteRequest):
    evidence_limit: int = Field(default=5, ge=0, le=20)


class VectorRunResponse(APIModel):
    agent: Literal["vector_agent_day10"] = "vector_agent_day10"
    status: VectorRunStatus
    route: VectorRoute
    question: str
    route_decision: VectorRouteDecision
    search: VectorSearchResponse | None = None
    answer: str
    evidence: list[VectorMatch] = Field(default_factory=list)
    evidence_limited: bool = False
    tool_trace: list[VectorToolTrace]
    total_elapsed_ms: float = Field(ge=0)
    execution_allowed: bool = False

    @model_validator(mode="after")
    def validate_run(self) -> "VectorRunResponse":
        if self.status == VectorRunStatus.completed:
            if self.search is None or not self.execution_allowed:
                raise ValueError("completed vector runs require search execution")
        else:
            if self.search is not None or self.execution_allowed:
                raise ValueError("blocked vector runs cannot contain search results")
        return self
