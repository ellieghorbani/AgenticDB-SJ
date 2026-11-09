"""Tests for the Day 10 vector orchestration workflow."""

from app.copilot.vector_orchestrator import VectorAgentOrchestrator
from app.copilot.vector_router import DeterministicVectorRouter
from app.models.vector import (
    VectorEntityType,
    VectorMatch,
    VectorSearchResponse,
)


class FakeSearchService:
    def search(self, request):
        return VectorSearchResponse(
            model="sentence-transformers/all-MiniLM-L6-v2",
            dimensions=384,
            query=request.query,
            entity_types=request.entity_types,
            only_open_parks=request.only_open_parks,
            education_level_code=request.education_level_code,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
            match_count=1,
            matches=[
                VectorMatch(
                    document_id=1,
                    entity_type=VectorEntityType.park,
                    entity_id="3",
                    title="Bascom Community Center and Library",
                    source_text="Real source-derived park text.",
                    similarity=0.91,
                    metadata={"current_status": "Open"},
                )
            ],
            elapsed_ms=2.0,
            database_role="agenticdb_reader",
            transaction_read_only=True,
        )


def test_completed_vector_run_contains_evidence():
    orchestrator = VectorAgentOrchestrator(
        DeterministicVectorRouter(),
        FakeSearchService(),
    )
    response = orchestrator.run(
        "Find open park features related to community centers and libraries.",
        evidence_limit=1,
    )
    assert response.status.value == "completed"
    assert response.route.value == "hybrid_vector"
    assert response.search is not None
    assert response.search.database_role == "agenticdb_reader"
    assert len(response.evidence) == 1
    assert [item.tool for item in response.tool_trace] == [
        "vector.route",
        "vector.search",
        "answer.synthesize",
    ]


def test_unsafe_vector_run_skips_search():
    orchestrator = VectorAgentOrchestrator(
        DeterministicVectorRouter(),
        FakeSearchService(),
    )
    response = orchestrator.run("Delete all park embeddings.")
    assert response.status.value == "blocked"
    assert response.search is None
    assert response.execution_allowed is False
    assert response.tool_trace[1].status == "skipped"
