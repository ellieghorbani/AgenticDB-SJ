"""Day 6 schema-retrieval and structured-planning endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_planner_service, get_schema_catalog_service
from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.schema_catalog import SchemaCatalogService
from app.copilot.schema_retrieval import SchemaRetriever
from app.models.copilot import (
    PlanRequest,
    PlanResponse,
    SchemaCatalogResponse,
    SchemaContextRequest,
    SchemaContextResponse,
)

router = APIRouter(prefix="/api/v1/copilot", tags=["copilot"])


@router.get("/schema", response_model=SchemaCatalogResponse)
def schema_catalog(
    service: Annotated[SchemaCatalogService, Depends(get_schema_catalog_service)],
) -> SchemaCatalogResponse:
    """Return the actual, allowlisted database schema available to the copilot."""

    return service.catalog()


@router.post("/schema/retrieve", response_model=SchemaContextResponse)
def retrieve_schema_context(
    request: SchemaContextRequest,
    service: Annotated[SchemaCatalogService, Depends(get_schema_catalog_service)],
) -> SchemaContextResponse:
    """Rank the relevant allowlisted relations for a natural-language question."""

    return SchemaRetriever(service.catalog()).retrieve(
        request.question,
        top_k=request.top_k,
    )


@router.post("/plan", response_model=PlanResponse)
def create_query_plan(
    request: PlanRequest,
    planner: Annotated[RuleBasedQueryPlanner, Depends(get_planner_service)],
) -> PlanResponse:
    """Create a typed, non-executable query plan. No SQL is generated or run."""

    return planner.plan(request.question, top_k=request.top_k)
