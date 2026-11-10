"""Unit tests for the OpenAI Responses structured planning adapter."""

from types import SimpleNamespace

from app.copilot.llm_provider import OpenAIResponsesPlanningProvider
from app.models.copilot import PlannerIntent
from app.models.llm import LLMPlanProposal


class FakeResponsesResource:
    def __init__(self):
        self.kwargs = None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            id="resp_123",
            model="fake-model",
            output_parsed=LLMPlanProposal(
                intent=PlannerIntent.schools_per_neighborhood,
                confidence=0.95,
                minimum_school_count=None,
                minimum_park_count=None,
                distance_value=None,
                distance_unit=None,
                neighborhood_name=None,
                requires_clarification=False,
                clarification_question=None,
                rationale="The user asks for counts by neighborhood.",
            ),
            usage=SimpleNamespace(
                input_tokens=80,
                output_tokens=20,
                total_tokens=100,
            ),
        )


class FakeClient:
    def __init__(self):
        self.responses = FakeResponsesResource()


def test_responses_provider_uses_strict_pydantic_output_and_records_usage():
    client = FakeClient()
    provider = OpenAIResponsesPlanningProvider(
        api_key="test-key",
        model="fake-model",
        input_cost_per_million=1.0,
        output_cost_per_million=2.0,
        client=client,
    )

    result = provider.propose(
        "Count schools by neighborhood.",
        "core.neighborhoods and app.school_neighborhoods",
    )

    assert result.proposal.intent == PlannerIntent.schools_per_neighborhood
    assert result.usage.api_called is True
    assert result.usage.total_tokens == 100
    assert result.usage.estimated_cost_usd == 0.00012
    assert client.responses.kwargs["text_format"] is LLMPlanProposal
    assert client.responses.kwargs["store"] is False
