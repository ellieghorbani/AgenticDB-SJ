"""Unit tests for deterministic Day 7 SQL generation."""

import json
from pathlib import Path

import pytest

from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.schema_catalog import build_static_catalog
from app.copilot.sql_generator import TemplateSQLGenerator

CASES_PATH = Path(__file__).resolve().parents[2] / "benchmarks/day7/sql_generation_cases.json"
CASES = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]


@pytest.fixture(scope="module")
def generator():
    return TemplateSQLGenerator(RuleBasedQueryPlanner(build_static_catalog()))


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_sql_generation_cases(generator, case):
    response = generator.generate(case["question"])
    assert response.intent.value == case["expected_intent"]
    assert response.status.value == case["expected_status"]
    assert set(case["required_relations"]).issubset(response.relations)
    assert [parameter.value for parameter in response.parameters] == case[
        "expected_parameter_values"
    ]
    assert response.execution_allowed is False

    if response.status.value == "generated":
        assert response.sql
        assert response.sql_generated is True
        assert response.sql.count("%s") == len(response.parameters)
        assert all(check.passed for check in response.safety_checks)
    else:
        assert response.sql is None
        assert response.sql_generated is False
        assert response.parameters == []


def test_dynamic_distance_is_parameterized(generator):
    response = generator.generate(
        "Which active elementary schools are within 2.5 kilometers of an open park?"
    )
    assert response.status.value == "generated"
    assert response.parameters[1].name == "distance_meters"
    assert response.parameters[1].value == 2500.0
    assert "2500" not in response.sql


def test_dynamic_thresholds_are_parameterized(generator):
    response = generator.generate(
        "Which neighborhoods contain at least four active schools and five open parks?"
    )
    assert [parameter.value for parameter in response.parameters] == [4, 5]
    assert response.sql.count("%s") == 2


def test_no_generated_query_is_executable(generator):
    for case in CASES:
        assert generator.generate(case["question"]).execution_allowed is False
