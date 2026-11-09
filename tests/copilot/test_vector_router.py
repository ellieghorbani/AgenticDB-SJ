"""Tests for the Day 10 deterministic vector router."""

from app.copilot.vector_router import DeterministicVectorRouter
from app.models.vector import VectorEntityType, VectorRoute


def test_routes_semantic_park_question():
    decision = DeterministicVectorRouter().route(
        "Find park features similar to walking and biking trails."
    )
    assert decision.route == VectorRoute.semantic_vector
    assert decision.entity_types == [VectorEntityType.park]
    assert decision.execution_allowed is True


def test_routes_open_park_question_to_hybrid_filter():
    decision = DeterministicVectorRouter().route(
        "Find open park features related to community centers and libraries."
    )
    assert decision.route == VectorRoute.hybrid_vector
    assert decision.only_open_parks is True


def test_routes_elementary_school_question_to_hybrid_filter():
    decision = DeterministicVectorRouter().route(
        "Find schools related to elementary education."
    )
    assert decision.route == VectorRoute.hybrid_vector
    assert decision.education_level_code == "ELEM"


def test_blocks_write_request():
    decision = DeterministicVectorRouter().route("Delete all park embeddings.")
    assert decision.route == VectorRoute.blocked
    assert decision.execution_allowed is False


def test_rejects_unknown_domain():
    decision = DeterministicVectorRouter().route(
        "Find family-friendly concerts this weekend."
    )
    assert decision.route == VectorRoute.unsupported
    assert decision.execution_allowed is False


def test_explicit_neighborhood_takes_precedence_over_garden_alias():
    decision = DeterministicVectorRouter().route(
        "Find neighborhoods related to Rose Garden."
    )

    assert decision.route == VectorRoute.semantic_vector
    assert decision.entity_types == [
        VectorEntityType.neighborhood
    ]
    assert decision.execution_allowed is True
