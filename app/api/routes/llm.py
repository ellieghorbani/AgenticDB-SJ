"""Day 11 OpenAI-assisted planning and agent endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import (
    get_llm_agent_orchestrator,
    get_llm_planning_service,
)
from app.core.config import Settings, get_settings
from app.copilot.llm_orchestrator import LLMAssistedAgentOrchestrator
from app.copilot.llm_planner import LLMAssistedPlanningService
from app.models.llm import (
    LLMAgentRunRequest,
    LLMAgentRunResponse,
    LLMPlanRequest,
    LLMPlanResponse,
    LLMProviderStatusResponse,
)

router = APIRouter(prefix="/api/v1/copilot/llm", tags=["llm"])


@router.get("/status", response_model=LLMProviderStatusResponse)
def llm_status(
    settings: Annotated[Settings, Depends(get_settings)],
) -> LLMProviderStatusResponse:
    key_configured = settings.openai_api_key_configured
    status = (
        "ready"
        if settings.planning_provider == "deterministic" or key_configured
        else "configuration_required"
    )
    return LLMProviderStatusResponse(
        status=status,
        planning_provider=settings.planning_provider,
        openai_api_key_configured=key_configured,
        openai_llm_model=settings.openai_llm_model,
        deterministic_fallback_enabled=settings.openai_fallback_to_deterministic,
        embedding_provider=settings.embedding_provider,
        active_embedding_model=settings.active_embedding_model_key,
        active_embedding_dimensions=settings.active_embedding_dimensions,
    )


@router.post("/plan", response_model=LLMPlanResponse)
def llm_plan(
    request: LLMPlanRequest,
    service: Annotated[
        LLMAssistedPlanningService,
        Depends(get_llm_planning_service),
    ],
) -> LLMPlanResponse:
    """Use deterministic or OpenAI structured planning; never generate SQL."""

    return service.plan(
        request.question,
        top_k=request.top_k,
        requested_provider=request.provider,
    )


@router.post("/run", response_model=LLMAgentRunResponse)
def llm_run(
    request: LLMAgentRunRequest,
    orchestrator: Annotated[
        LLMAssistedAgentOrchestrator,
        Depends(get_llm_agent_orchestrator),
    ],
) -> LLMAgentRunResponse:
    """Run an LLM-assisted plan through deterministic SQL safety layers."""

    return orchestrator.run(
        request.question,
        top_k=request.top_k,
        evidence_limit=request.evidence_limit,
        requested_provider=request.provider,
    )
