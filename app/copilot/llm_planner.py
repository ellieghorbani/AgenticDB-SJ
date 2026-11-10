"""OpenAI-assisted typed planning with a deterministic safety fallback."""

from __future__ import annotations

from app.copilot.llm_provider import (
    PlanningProviderError,
    StructuredPlanningProvider,
)
from app.copilot.planner import RuleBasedQueryPlanner
from app.models.copilot import (
    PlannerIntent,
    QueryPlan,
    SchemaCatalogResponse,
    SchemaContextResponse,
)
from app.models.llm import (
    LLMPlanProposal,
    LLMPlanResponse,
    ModelUsage,
    RequestedPlanningProvider,
)


class LLMAssistedPlanningService:
    """Use an LLM for intent/slot extraction, then rebuild a trusted typed plan.

    The model never returns SQL. Its proposal is translated into a canonical
    question and passed through the existing deterministic typed planner. This
    preserves reviewed relation choices and downstream SQL templates.
    """

    planner_name = "openai_assisted_planner_day11"

    def __init__(
        self,
        deterministic_planner: RuleBasedQueryPlanner,
        catalog: SchemaCatalogResponse,
        *,
        provider: StructuredPlanningProvider | None,
        default_provider: str = "deterministic",
        fallback_to_deterministic: bool = True,
    ):
        self.deterministic_planner = deterministic_planner
        self.catalog = catalog
        self.provider = provider
        self.default_provider = default_provider
        self.fallback_to_deterministic = fallback_to_deterministic

    def plan(
        self,
        question: str,
        *,
        top_k: int = 6,
        requested_provider: RequestedPlanningProvider = RequestedPlanningProvider.default,
    ) -> LLMPlanResponse:
        normalized = " ".join(question.strip().split())
        baseline = self.deterministic_planner.plan(normalized, top_k=top_k)

        # Destructive requests are blocked locally and never sent to an API.
        if baseline.plan.intent == PlannerIntent.unsafe_request:
            return LLMPlanResponse(
                planner=self.planner_name,
                provider_requested=requested_provider,
                provider_used="local_safety_gate",
                fallback_used=False,
                model=None,
                proposal=None,
                plan=baseline.plan,
                schema_context=baseline.schema_context,
                usage=ModelUsage(api_called=False),
                warnings=[
                    "The local safety gate blocked the request before any hosted model call."
                ],
            )

        provider_choice = self._provider_choice(requested_provider)
        if provider_choice == "deterministic":
            return self._deterministic_response(
                normalized,
                top_k,
                requested_provider,
                provider_used="deterministic",
                fallback_used=False,
            )

        if self.provider is None:
            return self._fallback_or_raise(
                normalized,
                top_k,
                requested_provider,
                "OpenAI planning was requested, but OPENAI_API_KEY is not configured.",
            )

        try:
            provider_result = self.provider.propose(
                normalized,
                self._schema_summary(),
            )
        except PlanningProviderError as exc:
            return self._fallback_or_raise(
                normalized,
                top_k,
                requested_provider,
                f"OpenAI planning failed: {exc}",
            )

        proposal = provider_result.proposal
        canonical_question = self._canonical_question(proposal)
        trusted = self.deterministic_planner.plan(canonical_question, top_k=top_k)

        requires_clarification = (
            proposal.requires_clarification
            or trusted.plan.requires_clarification
        )
        warnings = list(trusted.plan.warnings)
        if proposal.clarification_question:
            warnings.append(proposal.clarification_question)
        warnings.append(
            "The hosted model selected an intent and extracted slots; "
            "the final typed plan was rebuilt by the deterministic allowlisted planner."
        )

        plan = trusted.plan.model_copy(
            update={
                "question": normalized,
                "confidence": proposal.confidence,
                "requires_clarification": requires_clarification,
                "warnings": warnings,
            }
        )
        context = trusted.schema_context.model_copy(update={"question": normalized})
        return LLMPlanResponse(
            planner=self.planner_name,
            provider_requested=requested_provider,
            provider_used="openai",
            fallback_used=False,
            model=self.provider.model,
            proposal=proposal,
            plan=plan,
            schema_context=context,
            usage=provider_result.usage,
            warnings=[],
        )

    def _provider_choice(
        self,
        requested: RequestedPlanningProvider,
    ) -> str:
        if requested == RequestedPlanningProvider.deterministic:
            return "deterministic"
        if requested == RequestedPlanningProvider.openai:
            return "openai"
        return self.default_provider

    def _deterministic_response(
        self,
        question: str,
        top_k: int,
        requested_provider: RequestedPlanningProvider,
        *,
        provider_used: str,
        fallback_used: bool,
        warning: str | None = None,
    ) -> LLMPlanResponse:
        result = self.deterministic_planner.plan(question, top_k=top_k)
        warnings = [warning] if warning else []
        return LLMPlanResponse(
            planner=self.planner_name,
            provider_requested=requested_provider,
            provider_used=provider_used,
            fallback_used=fallback_used,
            model=None,
            proposal=None,
            plan=result.plan,
            schema_context=result.schema_context,
            usage=ModelUsage(api_called=False),
            warnings=warnings,
        )

    def _fallback_or_raise(
        self,
        question: str,
        top_k: int,
        requested_provider: RequestedPlanningProvider,
        message: str,
    ) -> LLMPlanResponse:
        if not self.fallback_to_deterministic:
            raise PlanningProviderError(message)
        return self._deterministic_response(
            question,
            top_k,
            requested_provider,
            provider_used="deterministic_fallback",
            fallback_used=True,
            warning=message,
        )

    def _schema_summary(self) -> str:
        lines = [
            "Geographic scope: San Jose neighborhood polygons and active public schools.",
            "Only the following allowlisted relations and source fields are available:",
        ]
        for relation in self.catalog.relations:
            columns = ", ".join(column.name for column in relation.columns)
            lines.append(
                f"- {relation.qualified_name}: {relation.description} "
                f"Columns: {columns}."
            )
        lines.append(
            "Open park feature means a City park-dataset record with current_status = Open."
        )
        lines.append(
            "The system supports only the fixed intent enum supplied in the output schema."
        )
        return "\n".join(lines)

    @staticmethod
    def _canonical_question(proposal: LLMPlanProposal) -> str:
        intent = proposal.intent
        distance = proposal.distance_value or 1.0
        unit = proposal.distance_unit or "miles"
        school_minimum = proposal.minimum_school_count or 3
        park_minimum = proposal.minimum_park_count or 2

        if intent == PlannerIntent.schools_per_neighborhood:
            return "How many active public schools are located in each neighborhood?"
        if intent == PlannerIntent.open_parks_per_neighborhood:
            return "Which neighborhoods intersect the most open park-dataset features?"
        if intent == PlannerIntent.elementary_schools_near_open_parks:
            return (
                "Which active elementary schools are within "
                f"{distance:g} {unit} of an open park feature?"
            )
        if intent == PlannerIntent.nearest_open_park_per_school:
            return "What is the nearest open park feature to each active school?"
        if intent == PlannerIntent.open_parks_intersecting_neighborhood:
            if proposal.neighborhood_name:
                return (
                    "Which open park features intersect the "
                    f"{proposal.neighborhood_name} neighborhood?"
                )
            return "Which open park features intersect neighborhoods?"
        if intent == PlannerIntent.neighborhoods_with_minimum_schools_and_parks:
            return (
                "Which neighborhoods contain at least "
                f"{school_minimum} active schools and {park_minimum} "
                "open park features?"
            )
        if intent == PlannerIntent.schools_without_nearby_open_park:
            return (
                "Which active schools have no open park feature within "
                f"{distance:g} {unit}?"
            )
        if intent == PlannerIntent.average_nearest_park_distance_by_neighborhood:
            return (
                "What is the average nearest-open-park distance for active "
                "schools by neighborhood?"
            )
        if intent == PlannerIntent.open_parks_with_most_nearby_schools:
            return (
                "Which open park features have the most active schools within "
                f"{distance:g} {unit}?"
            )
        if intent == PlannerIntent.neighborhoods_with_elementary_and_high_schools:
            return (
                "Which neighborhoods contain both active elementary and active "
                "high-school records?"
            )
        if intent == PlannerIntent.unsafe_request:
            return "Delete all schools and drop the parks table."
        return "Find family-friendly concerts this weekend."
