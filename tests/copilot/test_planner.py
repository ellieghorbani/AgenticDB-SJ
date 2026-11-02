"""Tests for the non-executable Day 6 planner."""

import pytest

from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.schema_catalog import build_static_catalog
from app.models.copilot import PlannerIntent, QueryType


@pytest.fixture
def planner():
    return RuleBasedQueryPlanner(build_static_catalog())


@pytest.mark.parametrize(
    ("question", "intent", "query_type"),
    [
        (
            "How many active public schools are located in each neighborhood?",
            PlannerIntent.schools_per_neighborhood,
            QueryType.aggregate,
        ),
        (
            "Which neighborhoods intersect the most open park-dataset features?",
            PlannerIntent.open_parks_per_neighborhood,
            QueryType.spatial,
        ),
        (
            "Which active elementary schools are within one mile of an open park feature?",
            PlannerIntent.elementary_schools_near_open_parks,
            QueryType.spatial,
        ),
        (
            "What is the nearest open park feature to each active school?",
            PlannerIntent.nearest_open_park_per_school,
            QueryType.spatial,
        ),
        (
            "Which open park features intersect the Almaden Lake neighborhood?",
            PlannerIntent.open_parks_intersecting_neighborhood,
            QueryType.spatial,
        ),
        (
            "Which neighborhoods contain at least three active schools and two open park features?",
            PlannerIntent.neighborhoods_with_minimum_schools_and_parks,
            QueryType.hybrid,
        ),
        (
            "Which active schools have no open park feature within one mile?",
            PlannerIntent.schools_without_nearby_open_park,
            QueryType.spatial,
        ),
        (
            "What is the average nearest-open-park distance for active schools by neighborhood?",
            PlannerIntent.average_nearest_park_distance_by_neighborhood,
            QueryType.hybrid,
        ),
        (
            "Which open park features have the most active schools within one mile?",
            PlannerIntent.open_parks_with_most_nearby_schools,
            QueryType.hybrid,
        ),
        (
            "Which neighborhoods contain both active elementary and active high-school records?",
            PlannerIntent.neighborhoods_with_elementary_and_high_schools,
            QueryType.aggregate,
        ),
    ],
)
def test_day4_questions_map_to_expected_plans(planner, question, intent, query_type):
    response = planner.plan(question)
    assert response.plan.intent == intent
    assert response.plan.query_type == query_type
    assert response.plan.execution_allowed is False
    assert response.plan.sql_generated is False
    assert response.plan.relations


def test_thresholds_are_extracted(planner):
    response = planner.plan(
        "Which neighborhoods contain at least three active schools and two open park features?"
    )
    values = {item.field: item.value for item in response.plan.filters}
    assert values["active_school_count"] == 3
    assert values["open_park_feature_count"] == 2


def test_one_mile_is_normalized_to_meters(planner):
    response = planner.plan(
        "Which elementary schools are within one mile of an open park?"
    )
    assert response.plan.spatial_constraint is not None
    assert response.plan.spatial_constraint.distance_meters == pytest.approx(1609.344)


def test_unsafe_request_is_never_executable(planner):
    response = planner.plan("Delete all schools and drop the parks table")
    assert response.plan.intent == PlannerIntent.unsafe_request
    assert response.plan.query_type == QueryType.unsupported
    assert response.plan.execution_allowed is False
    assert response.plan.sql_generated is False
    assert response.schema_context.relations == []


def test_unsupported_domain_requires_clarification(planner):
    response = planner.plan("Find family-friendly concerts this weekend")
    assert response.plan.intent == PlannerIntent.unsupported
    assert response.plan.requires_clarification is True
