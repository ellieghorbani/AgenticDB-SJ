"""Unit tests for deterministic Day 9 answer synthesis."""

from app.copilot.answer_synthesis import DeterministicAnswerSynthesizer
from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.schema_catalog import build_static_catalog


def planner():
    return RuleBasedQueryPlanner(build_static_catalog())


def test_school_count_answer_uses_returned_rows_and_preserves_ties():
    plan = planner().plan(
        "How many active public schools are located in each neighborhood?"
    ).plan
    rows = [
        {
            "neighborhood_id": "A",
            "neighborhood_name": "Mayfair",
            "active_school_count": 6,
        },
        {
            "neighborhood_id": "B",
            "neighborhood_name": "Orchard",
            "active_school_count": 6,
        },
    ]
    answer = DeterministicAnswerSynthesizer().synthesize(
        plan,
        rows,
        sources=["core.neighborhoods", "app.school_neighborhoods"],
        query_fingerprint="abc123",
        evidence_limit=1,
    )

    assert "Mayfair" in answer.text
    assert "Orchard" in answer.text
    assert answer.row_count == 2
    assert len(answer.evidence) == 1
    assert answer.evidence_limited is True
    assert answer.query_fingerprint == "abc123"


def test_zero_result_answer_does_not_invent_rows():
    plan = planner().plan(
        "Which active schools have no open park feature within one mile?"
    ).plan
    answer = DeterministicAnswerSynthesizer().synthesize(
        plan,
        [],
        sources=["app.san_jose_active_schools_spatial", "core.parks"],
        query_fingerprint="empty123",
        evidence_limit=5,
    )

    assert answer.text == "No database rows matched the validated query."
    assert answer.row_count == 0
    assert answer.evidence == []
    assert answer.evidence_limited is False
