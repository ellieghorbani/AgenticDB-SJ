"""Day 9 agent tool-catalog and orchestration endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_agent_orchestrator
from app.copilot.agent_orchestrator import AgentOrchestrator
from app.copilot.tools import build_agent_tool_catalog
from app.models.agent import (
    AgentRunRequest,
    AgentRunResponse,
    AgentToolCatalogResponse,
)

router = APIRouter(prefix="/api/v1/copilot/agent", tags=["agent"])


@router.get("/tools", response_model=AgentToolCatalogResponse)
def agent_tools() -> AgentToolCatalogResponse:
    """Return the fixed tools and safety boundaries available to the agent."""

    return build_agent_tool_catalog()


@router.post("/run", response_model=AgentRunResponse)
def run_agent(
    request: AgentRunRequest,
    orchestrator: Annotated[AgentOrchestrator, Depends(get_agent_orchestrator)],
) -> AgentRunResponse:
    """Run one traced, evidence-backed, controlled agent workflow."""

    return orchestrator.run(
        request.question,
        top_k=request.top_k,
        evidence_limit=request.evidence_limit,
    )
