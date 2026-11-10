"""Typed contracts for the AgenticDB-SJ v1.0 release dashboard."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from app.models.api import APIModel


class BenchmarkMetric(APIModel):
    key: str
    label: str
    source: str
    passed: int = Field(ge=0)
    total: int = Field(ge=0)
    pass_rate: float = Field(ge=0, le=1)
    mean_latency_ms: float | None = Field(default=None, ge=0)
    p95_latency_ms: float | None = Field(default=None, ge=0)


class DataSnapshot(APIModel):
    neighborhoods: int = Field(ge=0)
    parks: int = Field(ge=0)
    schools: int = Field(ge=0)
    schools_in_scope: int = Field(ge=0)
    open_park_features: int = Field(ge=0)
    semantic_documents: int = Field(ge=0)
    embedded_vectors: int = Field(ge=0)
    embedding_models: dict[str, int] = Field(default_factory=dict)


class DatabaseReleaseInfo(APIModel):
    postgresql_version: str
    postgis_version: str
    pgvector_version: str
    hnsw_index_present: bool
    execution_role: str


class LLMReleaseInfo(APIModel):
    model: str | None = None
    intent_accuracy: float | None = Field(default=None, ge=0, le=1)
    deterministic_intent_accuracy: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)


class EmbeddingComparisonInfo(APIModel):
    case_count: int = Field(default=0, ge=0)
    mean_overlap_at_10: float | None = Field(default=None, ge=0)
    mean_jaccard_at_10: float | None = Field(default=None, ge=0, le=1)
    local_mean_latency_ms: float | None = Field(default=None, ge=0)
    openai_mean_latency_ms: float | None = Field(default=None, ge=0)


class ReleaseMetricsResponse(APIModel):
    status: Literal["ready", "not_built"]
    project: str = "AgenticDB-SJ"
    version: str
    generated_at: str | None = None
    all_benchmarks_passed: bool | None = None
    benchmark_count: int = Field(default=0, ge=0)
    aggregate_passed: int = Field(default=0, ge=0)
    aggregate_total: int = Field(default=0, ge=0)
    aggregate_pass_rate: float | None = Field(default=None, ge=0, le=1)
    benchmarks: list[BenchmarkMetric] = Field(default_factory=list)
    data_snapshot: DataSnapshot | None = None
    database: DatabaseReleaseInfo | None = None
    llm: LLMReleaseInfo | None = None
    embedding_comparison: EmbeddingComparisonInfo | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    extra_metrics: dict[str, Any] = Field(default_factory=dict)
