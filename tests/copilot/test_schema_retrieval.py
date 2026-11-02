"""Tests for deterministic schema retrieval."""

from app.copilot.schema_catalog import build_static_catalog
from app.copilot.schema_retrieval import SchemaRetriever


def test_school_park_question_retrieves_school_and_park_relations():
    retriever = SchemaRetriever(build_static_catalog())
    context = retriever.retrieve(
        "Which elementary schools are within one mile of an open park?",
        top_k=6,
    )
    names = {item.relation.qualified_name for item in context.relations}
    assert "app.san_jose_active_schools_spatial" in names or "core.schools" in names
    assert "core.parks" in names


def test_neighborhood_aggregate_retrieves_joinable_relations():
    retriever = SchemaRetriever(build_static_catalog())
    context = retriever.retrieve(
        "How many active public schools are located in each neighborhood?",
        top_k=6,
    )
    names = {item.relation.qualified_name for item in context.relations}
    assert "core.neighborhoods" in names
    assert "app.school_neighborhoods" in names
    assert any(
        join.left_relation == "core.neighborhoods"
        and join.right_relation == "app.school_neighborhoods"
        for join in context.joins
    )


def test_retrieval_respects_top_k():
    retriever = SchemaRetriever(build_static_catalog())
    context = retriever.retrieve("schools parks neighborhoods", top_k=2)
    assert len(context.relations) <= 2
