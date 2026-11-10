"""Day 11 OpenAI-assisted agent orchestration over existing safety layers."""

from __future__ import annotations

from time import perf_counter

from app.core.config import Settings
from app.copilot.agent_orchestrator import AgentOrchestrator
from app.copilot.answer_synthesis import DeterministicAnswerSynthesizer
from app.copilot.llm_planner import LLMAssistedPlanningService
from app.copilot.sql_execution import ReadOnlySQLExecutor
from app.copilot.sql_generator import TemplateSQLGenerator
from app.copilot.sql_validator import SQLASTValidator
from app.models.copilot import PlanResponse
from app.models.llm import (
    LLMAgentRunResponse,
    RequestedPlanningProvider,
)


class _PrecomputedPlanner:
    """Expose one already-built plan through the Day 9 planner interface."""

    def __init__(self, planning_response):
        self.planning_response = planning_response

    def plan(self, question: str, top_k: int = 6) -> PlanResponse:
        del question, top_k
        return PlanResponse(
            planner="rule_based_day6",
            plan=self.planning_response.plan,
            schema_context=self.planning_response.schema_context,
        )


class LLMAssistedAgentOrchestrator:
    """Call an LLM once for planning, then reuse the reviewed Day 7-9 chain."""

    def __init__(
        self,
        *,
        planning_service: LLMAssistedPlanningService,
        generator: TemplateSQLGenerator,
        validator: SQLASTValidator,
        executor: ReadOnlySQLExecutor,
        synthesizer: DeterministicAnswerSynthesizer,
        settings: Settings,
    ):
        self.planning_service = planning_service
        self.generator = generator
        self.validator = validator
        self.executor = executor
        self.synthesizer = synthesizer
        self.settings = settings

    def run(
        self,
        question: str,
        *,
        top_k: int = 6,
        evidence_limit: int = 5,
        requested_provider: RequestedPlanningProvider = RequestedPlanningProvider.default,
    ) -> LLMAgentRunResponse:
        started = perf_counter()
        planning = self.planning_service.plan(
            question,
            top_k=top_k,
            requested_provider=requested_provider,
        )
        agent = AgentOrchestrator(
            planner=_PrecomputedPlanner(planning),
            generator=self.generator,
            validator=self.validator,
            executor=self.executor,
            synthesizer=self.synthesizer,
            settings=self.settings,
        )
        run = agent.run(
            planning.plan.question,
            top_k=top_k,
            evidence_limit=evidence_limit,
        )
        return LLMAgentRunResponse(
            planning=planning,
            run=run,
            total_elapsed_ms=round((perf_counter() - started) * 1000.0, 3),
        )
