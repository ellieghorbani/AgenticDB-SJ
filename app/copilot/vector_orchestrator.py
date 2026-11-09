"""Traced Day 10 vector-search workflow."""

from __future__ import annotations

from time import perf_counter

from app.copilot.vector_router import DeterministicVectorRouter
from app.copilot.vector_search import VectorSearchService
from app.models.vector import (
    VectorRoute,
    VectorRunResponse,
    VectorRunStatus,
    VectorSearchRequest,
    VectorToolTrace,
)


class VectorAgentOrchestrator:
    agent_name = "vector_agent_day10"

    def __init__(
        self,
        router: DeterministicVectorRouter,
        search_service: VectorSearchService,
    ):
        self.router = router
        self.search_service = search_service

    def run(
        self,
        question: str,
        *,
        top_k: int = 5,
        min_similarity: float = 0.20,
        evidence_limit: int = 5,
    ) -> VectorRunResponse:
        overall = perf_counter()
        trace: list[VectorToolTrace] = []

        started = perf_counter()
        decision = self.router.route(
            question,
            top_k=top_k,
            min_similarity=min_similarity,
        )
        trace.append(
            VectorToolTrace(
                sequence=1,
                tool="vector.route",
                status=(
                    "succeeded"
                    if decision.execution_allowed
                    else "blocked"
                ),
                elapsed_ms=self._elapsed(started),
                message=decision.reason,
                output_summary={
                    "route": decision.route.value,
                    "entity_types": [item.value for item in decision.entity_types],
                },
            )
        )

        if not decision.execution_allowed:
            trace.append(
                VectorToolTrace(
                    sequence=2,
                    tool="vector.search",
                    status="skipped",
                    elapsed_ms=0.0,
                    message="Search was skipped because routing did not grant execution.",
                )
            )
            answer = (
                "The request was blocked because it contains a destructive action."
                if decision.route == VectorRoute.blocked
                else "The question is outside the supported Day 10 vector-search patterns."
            )
            trace.append(
                VectorToolTrace(
                    sequence=3,
                    tool="answer.synthesize",
                    status="succeeded",
                    elapsed_ms=0.0,
                    message="Created a safe non-search response.",
                )
            )
            return VectorRunResponse(
                status=VectorRunStatus.blocked,
                route=decision.route,
                question=decision.question,
                route_decision=decision,
                answer=answer,
                tool_trace=trace,
                total_elapsed_ms=self._elapsed(overall),
                execution_allowed=False,
            )

        request = VectorSearchRequest(
            query=decision.query_text,
            entity_types=decision.entity_types,
            top_k=decision.top_k,
            min_similarity=decision.min_similarity,
            only_open_parks=decision.only_open_parks,
            education_level_code=decision.education_level_code,
        )
        started = perf_counter()
        search = self.search_service.search(request)
        trace.append(
            VectorToolTrace(
                sequence=2,
                tool="vector.search",
                status="succeeded",
                elapsed_ms=self._elapsed(started),
                message="Encoded the question and searched pgvector with metadata filters.",
                output_summary={
                    "match_count": search.match_count,
                    "database_role": search.database_role,
                    "transaction_read_only": search.transaction_read_only,
                },
            )
        )

        started = perf_counter()
        if search.matches:
            first = search.matches[0]
            answer = (
                f"Found {search.match_count} semantic matches. The highest-ranked "
                f"result is {first.title} with similarity {first.similarity:.3f}."
            )
        else:
            answer = "No semantic documents met the requested similarity and filters."
        evidence = search.matches[:evidence_limit]
        trace.append(
            VectorToolTrace(
                sequence=3,
                tool="answer.synthesize",
                status="succeeded",
                elapsed_ms=self._elapsed(started),
                message="Synthesized an answer only from vector-search matches.",
                output_summary={"evidence_count": len(evidence)},
            )
        )

        return VectorRunResponse(
            status=VectorRunStatus.completed,
            route=decision.route,
            question=decision.question,
            route_decision=decision,
            search=search,
            answer=answer,
            evidence=evidence,
            evidence_limited=search.match_count > len(evidence),
            tool_trace=trace,
            total_elapsed_ms=self._elapsed(overall),
            execution_allowed=True,
        )

    @staticmethod
    def _elapsed(started: float) -> float:
        return round((perf_counter() - started) * 1000.0, 3)
