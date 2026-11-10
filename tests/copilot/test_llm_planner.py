"""Unit tests for Day 11 OpenAI-assisted typed planning."""

from app.copilot.llm_planner import LLMAssistedPlanningService
from app.copilot.llm_provider import (
    PlanningProviderError,
    PlanningProviderResult,
)
from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.schema_catalog import build_static_catalog
from app.models.copilot import PlannerIntent
from app.models.llm import (
    LLMPlanProposal,
    ModelUsage,
    RequestedPlanningProvider,
)


class FakeProvider:
    provider_name = "fake_openai"
    model = "fake-model"

    def __init__(self, proposal):
        self.proposal = proposal
        self.calls = 0

    def propose(self, question, schema_summary):
        self.calls += 1
        assert question
        assert "core.neighborhoods" in schema_summary
        return PlanningProviderResult(
            proposal=self.proposal,
            usage=ModelUsage(
                api_called=True,
                response_id="resp_test",
                model=self.model,
                input_tokens=100,
                output_tokens=20,
                total_tokens=120,
                elapsed_ms=5.0,
            ),
        )


class FailingProvider:
    provider_name = "fake_openai"
    model = "fake-model"

    def propose(self, question, schema_summary):
        del question, schema_summary
        raise PlanningProviderError("simulated provider outage")


def build_service(provider, *, fallback=True):
    catalog = build_static_catalog()
    return LLMAssistedPlanningService(
        RuleBasedQueryPlanner(catalog),
        catalog,
        provider=provider,
        default_provider="openai",
        fallback_to_deterministic=fallback,
    )


def test_openai_proposal_is_rebuilt_as_trusted_typed_plan():
    provider = FakeProvider(
        LLMPlanProposal(
            intent=PlannerIntent.neighborhoods_with_minimum_schools_and_parks,
            confidence=0.97,
            minimum_school_count=4,
            minimum_park_count=3,
            distance_value=None,
            distance_unit=None,
            neighborhood_name=None,
            requires_clarification=False,
            clarification_question=None,
            rationale="The question requests two neighborhood-level thresholds.",
        )
    )
    response = build_service(provider).plan(
        "Show areas with four schools and three parks.",
        requested_provider=RequestedPlanningProvider.openai,
    )

    assert response.provider_used == "openai"
    assert response.fallback_used is False
    assert response.plan.intent == PlannerIntent.neighborhoods_with_minimum_schools_and_parks
    assert [item.value for item in response.plan.filters] == [4, 3]
    assert response.plan.question == "Show areas with four schools and three parks."
    assert response.usage.total_tokens == 120
    assert provider.calls == 1


def test_unsafe_request_is_blocked_before_provider_call():
    provider = FakeProvider(
        LLMPlanProposal(
            intent=PlannerIntent.schools_per_neighborhood,
            confidence=1.0,
            minimum_school_count=None,
            minimum_park_count=None,
            distance_value=None,
            distance_unit=None,
            neighborhood_name=None,
            requires_clarification=False,
            clarification_question=None,
            rationale="Should never be used.",
        )
    )
    response = build_service(provider).plan(
        "Delete all schools and drop the parks table.",
        requested_provider=RequestedPlanningProvider.openai,
    )

    assert response.provider_used == "local_safety_gate"
    assert response.plan.intent == PlannerIntent.unsafe_request
    assert response.usage.api_called is False
    assert provider.calls == 0


def test_provider_failure_uses_deterministic_fallback():
    response = build_service(FailingProvider(), fallback=True).plan(
        "How many active public schools are located in each neighborhood?",
        requested_provider=RequestedPlanningProvider.openai,
    )

    assert response.provider_used == "deterministic_fallback"
    assert response.fallback_used is True
    assert response.plan.intent == PlannerIntent.schools_per_neighborhood
    assert response.usage.api_called is False
    assert "simulated provider outage" in response.warnings[0]


def test_missing_neighborhood_name_requires_clarification():
    provider = FakeProvider(
        LLMPlanProposal(
            intent=PlannerIntent.open_parks_intersecting_neighborhood,
            confidence=0.9,
            minimum_school_count=None,
            minimum_park_count=None,
            distance_value=None,
            distance_unit=None,
            neighborhood_name=None,
            requires_clarification=True,
            clarification_question="Which neighborhood should I use?",
            rationale="A neighborhood name is required.",
        )
    )
    response = build_service(provider).plan(
        "Which parks intersect a neighborhood?",
        requested_provider=RequestedPlanningProvider.openai,
    )

    assert response.plan.intent == PlannerIntent.open_parks_intersecting_neighborhood
    assert response.plan.requires_clarification is True
    assert "Which neighborhood" in " ".join(response.plan.warnings)
