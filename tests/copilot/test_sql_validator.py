"""Unit tests for Day 8 independent SQLGlot AST validation."""

import json
from pathlib import Path

import pytest

from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.schema_catalog import build_static_catalog
from app.copilot.sql_generator import TemplateSQLGenerator
from app.copilot.sql_validator import SQLASTValidator

CASES_PATH = (
    Path(__file__).resolve().parents[2]
    / "benchmarks/day8/validation_execution_cases.json"
)
BENCHMARK = json.loads(CASES_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def services():
    catalog = build_static_catalog()
    generator = TemplateSQLGenerator(RuleBasedQueryPlanner(catalog))
    validator = SQLASTValidator(catalog, max_result_rows=1000)
    return generator, validator


@pytest.mark.parametrize(
    "case",
    BENCHMARK["cases"][:10],
    ids=[case["id"] for case in BENCHMARK["cases"][:10]],
)
def test_supported_generated_queries_pass_ast_validation(services, case):
    generator, validator = services
    generation = generator.generate(case["question"])
    validation = validator.validate(generation)

    assert validation.status.value == "valid"
    assert validation.execution_allowed is True
    assert validation.statement_count == 1
    assert validation.root_expression == "Select"
    assert validation.outer_limit is not None
    assert validation.outer_limit <= 1000
    assert validation.query_fingerprint
    assert all(check.passed for check in validation.checks)


@pytest.mark.parametrize(
    "case",
    BENCHMARK["cases"][10:],
    ids=[case["id"] for case in BENCHMARK["cases"][10:]],
)
def test_blocked_or_unresolved_questions_never_gain_execution_permission(
    services,
    case,
):
    generator, validator = services
    validation = validator.validate(generator.generate(case["question"]))
    assert validation.status.value in {"blocked", "not_generated"}
    assert validation.execution_allowed is False


@pytest.mark.parametrize(
    "attack",
    BENCHMARK["adversarial_sql"],
    ids=[attack["id"] for attack in BENCHMARK["adversarial_sql"]],
)
def test_adversarial_sql_is_blocked_by_expected_ast_check(services, attack):
    generator, validator = services
    base = generator.generate(
        "How many active public schools are located in each neighborhood?"
    )
    tampered = base.model_copy(
        update={
            "sql": attack["sql"],
            "statement_type": (
                "WITH"
                if attack["sql"].lstrip().lower().startswith("with")
                else "SELECT"
            ),
            "sql_generated": True,
        }
    )
    validation = validator.validate(tampered)
    checks = {check.name: check.passed for check in validation.checks}

    assert validation.status.value == "blocked"
    assert validation.execution_allowed is False
    assert checks[attack["expected_failed_check"]] is False


def test_fingerprint_is_deterministic(services):
    generator, validator = services
    generation = generator.generate(
        "Which neighborhoods contain at least three active schools and two open parks?"
    )
    first = validator.validate(generation)
    second = validator.validate(generation)
    assert first.query_fingerprint == second.query_fingerprint
