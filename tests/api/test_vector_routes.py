"""HTTP contract tests for Day 10 vector endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_vector_orchestrator,
    get_vector_router,
    get_vector_search_service,
)
from app.copilot.vector_orchestrator import VectorAgentOrchestrator
from app.copilot.vector_router import DeterministicVectorRouter
from app.main import create_app
from app.models.vector import (
    VectorEntityType,
    VectorMatch,
    VectorSearchResponse,
    VectorStatusResponse,
)


class FakeVectorSearchService:
    def status(self):
        return VectorStatusResponse(
            status="ready",
            extension_version="0.8.7",
            document_count=1128,
            embedded_document_count=1128,
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            embedding_dimensions=384,
            entity_counts={"park": 611, "school": 220, "neighborhood": 297},
            hnsw_index_present=True,
        )

    def search(self, request):
        entity_type = request.entity_types[0]
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
                    entity_type=entity_type,
                    entity_id="example",
                    title="Example semantic result",
                    source_text="Real source-derived text.",
                    similarity=0.8,
                    metadata={"current_status": "Open"},
                )
            ],
            elapsed_ms=1.0,
            database_role="agenticdb_reader",
            transaction_read_only=True,
        )


@pytest.fixture
def vector_client(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "test-password")
    application = create_app()
    router = DeterministicVectorRouter()
    service = FakeVectorSearchService()
    orchestrator = VectorAgentOrchestrator(router, service)
    application.dependency_overrides[get_vector_router] = lambda: router
    application.dependency_overrides[get_vector_search_service] = lambda: service
    application.dependency_overrides[get_vector_orchestrator] = lambda: orchestrator
    with TestClient(application) as client:
        yield client
    application.dependency_overrides.clear()


def test_vector_status(vector_client):
    response = vector_client.get("/api/v1/copilot/vector/status")
    assert response.status_code == 200
    assert response.json()["document_count"] == 1128


def test_vector_route(vector_client):
    response = vector_client.post(
        "/api/v1/copilot/vector/route",
        json={
            "question": "Find open park features related to community centers."
        },
    )
    assert response.status_code == 200
    assert response.json()["route"] == "hybrid_vector"


def test_vector_search(vector_client):
    response = vector_client.post(
        "/api/v1/copilot/vector/search",
        json={
            "query": "community center",
            "entity_types": ["park"],
            "top_k": 5,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["match_count"] == 1
    assert payload["matches"][0]["entity_type"] == "park"


def test_vector_run(vector_client):
    response = vector_client.post(
        "/api/v1/copilot/vector/run",
        json={"question": "Find neighborhoods related to Rose Garden."},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_vector_run_rejects_raw_embedding(vector_client):
    response = vector_client.post(
        "/api/v1/copilot/vector/run",
        json={
            "question": "Find neighborhoods related to Rose Garden.",
            "embedding": [0.1, 0.2],
        },
    )
    assert response.status_code == 422
