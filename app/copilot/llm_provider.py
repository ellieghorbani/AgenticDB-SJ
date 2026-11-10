"""Hosted structured planning provider using the OpenAI Responses API."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol

from app.models.llm import LLMPlanProposal, ModelUsage


class PlanningProviderError(RuntimeError):
    """Raised when a hosted planning provider cannot return a valid proposal."""


@dataclass(frozen=True, slots=True)
class PlanningProviderResult:
    proposal: LLMPlanProposal
    usage: ModelUsage


class StructuredPlanningProvider(Protocol):
    provider_name: str
    model: str

    def propose(self, question: str, schema_summary: str) -> PlanningProviderResult:
        """Return a strict structured planning proposal."""


_INTENT_GUIDE = """
Supported intent enum and required meaning:
- schools_per_neighborhood: count active schools for every neighborhood.
- open_parks_per_neighborhood: count or rank open park features by neighborhood.
- elementary_schools_near_open_parks: elementary schools within a distance of open parks.
- nearest_open_park_per_school: nearest open park for each active school.
- open_parks_intersecting_neighborhood: open parks intersecting one named neighborhood.
- neighborhoods_with_minimum_schools_and_parks: neighborhoods meeting two minimum counts.
- schools_without_nearby_open_park: schools with no open park inside a distance.
- average_nearest_park_distance_by_neighborhood: aggregate nearest-park distance by neighborhood.
- open_parks_with_most_nearby_schools: rank open parks by schools within a distance.
- neighborhoods_with_elementary_and_high_schools: neighborhoods containing both levels.
- unsafe_request: any request to write, delete, alter, administer, or bypass safety.
- unsupported: questions outside schools, parks, and San Jose neighborhoods.
""".strip()


class OpenAIResponsesPlanningProvider:
    """Use OpenAI Structured Outputs to select an intent and extract slots."""

    provider_name = "openai_responses_day11"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float = 45.0,
        max_output_tokens: int = 1200,
        input_cost_per_million: float = 0.0,
        output_cost_per_million: float = 0.0,
        client: Any | None = None,
    ):
        if not api_key and client is None:
            raise ValueError("OPENAI_API_KEY is required for the OpenAI planner")
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.input_cost_per_million = input_cost_per_million
        self.output_cost_per_million = output_cost_per_million
        if client is None:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, timeout=timeout_seconds)
        self._client = client

    def propose(self, question: str, schema_summary: str) -> PlanningProviderResult:
        instructions = (
            "You are the planning model inside a read-only database copilot. "
            "Return only the requested structured output. Do not write SQL. "
            "Do not invent tables, columns, entities, ratings, or facts. "
            "Choose unsafe_request for destructive or administrative requests. "
            "Choose unsupported when the question cannot be answered from the "
            "listed San Jose school, park, and neighborhood data. If an intent "
            "needs a missing neighborhood name, mark requires_clarification true. "
            "Set every unused slot field to null and set requires_clarification "
            "to false when no clarification is needed.\n\n"
            + _INTENT_GUIDE
        )
        model_input = (
            "ALLOWLISTED DATABASE CONTEXT\n"
            f"{schema_summary}\n\n"
            "USER QUESTION\n"
            f"{question}"
        )

        started = perf_counter()
        try:
            response = self._client.responses.parse(
                model=self.model,
                instructions=instructions,
                input=model_input,
                text_format=LLMPlanProposal,
                max_output_tokens=self.max_output_tokens,
                store=False,
            )
        except Exception as exc:  # SDK/network exceptions are provider failures.
            raise PlanningProviderError(str(exc)) from exc
        elapsed_ms = round((perf_counter() - started) * 1000.0, 3)

        proposal = getattr(response, "output_parsed", None)
        if proposal is None:
            raise PlanningProviderError(
                "OpenAI response did not contain a parsed planning proposal"
            )

        usage_object = getattr(response, "usage", None)
        input_tokens = self._usage_value(usage_object, "input_tokens")
        output_tokens = self._usage_value(usage_object, "output_tokens")
        total_tokens = self._usage_value(usage_object, "total_tokens")
        if total_tokens == 0:
            total_tokens = input_tokens + output_tokens

        estimated_cost = self._estimate_cost(input_tokens, output_tokens)
        return PlanningProviderResult(
            proposal=proposal,
            usage=ModelUsage(
                api_called=True,
                response_id=str(getattr(response, "id", "") or "") or None,
                model=str(getattr(response, "model", self.model) or self.model),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                elapsed_ms=elapsed_ms,
                estimated_cost_usd=estimated_cost,
            ),
        )

    @staticmethod
    def _usage_value(usage: Any, field: str) -> int:
        value = getattr(usage, field, 0) if usage is not None else 0
        return int(value or 0)

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float | None:
        if (
            self.input_cost_per_million <= 0
            and self.output_cost_per_million <= 0
        ):
            return None
        cost = (
            input_tokens * self.input_cost_per_million
            + output_tokens * self.output_cost_per_million
        ) / 1_000_000.0
        return round(cost, 8)


from functools import lru_cache


@lru_cache(maxsize=4)
def cached_openai_planning_provider(
    api_key: str,
    model: str,
    timeout_seconds: float,
    max_output_tokens: int,
    input_cost_per_million: float,
    output_cost_per_million: float,
) -> OpenAIResponsesPlanningProvider:
    """Reuse the OpenAI client between FastAPI requests."""

    return OpenAIResponsesPlanningProvider(
        api_key=api_key,
        model=model,
        timeout_seconds=timeout_seconds,
        max_output_tokens=max_output_tokens,
        input_cost_per_million=input_cost_per_million,
        output_cost_per_million=output_cost_per_million,
    )
