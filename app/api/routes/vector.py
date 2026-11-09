"""Day 10 semantic-vector and hybrid metadata-filtered search endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import (
    get_vector_orchestrator,
    get_vector_router,
    get_vector_search_service,
)
from app.copilot.vector_orchestrator import VectorAgentOrchestrator
from app.copilot.vector_router import DeterministicVectorRouter
from app.copilot.vector_search import VectorSearchService
from app.models.vector import (
    VectorRouteDecision,
    VectorRouteRequest,
    VectorRunRequest,
    VectorRunResponse,
    VectorSearchRequest,
    VectorSearchResponse,
    VectorStatusResponse,
)

router = APIRouter(prefix="/api/v1/copilot/vector", tags=["vector"])


@router.get("/status", response_model=VectorStatusResponse)
def vector_status(
    service: Annotated[VectorSearchService, Depends(get_vector_search_service)],
) -> VectorStatusResponse:
    return service.status()


@router.post("/route", response_model=VectorRouteDecision)
def route_vector_question(
    request: VectorRouteRequest,
    vector_router: Annotated[DeterministicVectorRouter, Depends(get_vector_router)],
) -> VectorRouteDecision:
    return vector_router.route(
        request.question,
        top_k=request.top_k,
        min_similarity=request.min_similarity,
    )


@router.post("/search", response_model=VectorSearchResponse)
def search_vectors(
    request: VectorSearchRequest,
    service: Annotated[VectorSearchService, Depends(get_vector_search_service)],
) -> VectorSearchResponse:
    return service.search(request)


@router.post("/run", response_model=VectorRunResponse)
def run_vector_agent(
    request: VectorRunRequest,
    orchestrator: Annotated[
        VectorAgentOrchestrator,
        Depends(get_vector_orchestrator),
    ],
) -> VectorRunResponse:
    return orchestrator.run(
        request.question,
        top_k=request.top_k,
        min_similarity=request.min_similarity,
        evidence_limit=request.evidence_limit,
    )
