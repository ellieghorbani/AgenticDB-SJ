#!/usr/bin/env python3
"""Run the live Day 10 vector-routing and retrieval benchmark."""

from __future__ import annotations

import json
from pathlib import Path

from pgvector.psycopg import register_vector

from app.core.config import get_settings
from app.copilot.embeddings import cached_embedding_provider
from app.copilot.vector_orchestrator import VectorAgentOrchestrator
from app.copilot.vector_router import DeterministicVectorRouter
from app.copilot.vector_search import VectorSearchService
from app.db.connection import open_db_connection


BENCHMARK_PATH = Path("benchmarks/day10/vector_cases.json")
REPORT_PATH = Path("results/day10/vector_validation.json")


def _contains_any(values: list[str], terms: list[str]) -> bool:
    lowered = [value.lower() for value in values]
    return any(term.lower() in value for term in terms for value in lowered)


def main() -> None:
    settings = get_settings()
    connection = open_db_connection(settings)
    connection.execute("SET TRANSACTION READ ONLY")
    register_vector(connection)
    provider = cached_embedding_provider(
        settings.embedding_model_name,
        settings.embedding_dimensions,
        settings.embedding_device,
        settings.embedding_batch_size,
    )
    orchestrator = VectorAgentOrchestrator(
        DeterministicVectorRouter(),
        VectorSearchService(connection, settings, provider),
    )

    benchmark = json.loads(BENCHMARK_PATH.read_text())
    results = []
    passed_count = 0

    try:
        for case in benchmark["cases"]:
            response = orchestrator.run(
                case["question"],
                top_k=10,
                min_similarity=0.15,
                evidence_limit=5,
            )
            failures: list[str] = []
            if response.route.value != case["expected_route"]:
                failures.append(
                    f"route={response.route.value}, expected={case['expected_route']}"
                )

            if response.search is not None:
                actual_types = sorted(
                    {item.value for item in response.search.entity_types}
                )
                expected_types = sorted(case.get("expected_entity_types", []))
                if actual_types != expected_types:
                    failures.append(
                        f"entity_types={actual_types}, expected={expected_types}"
                    )
                if not response.search.transaction_read_only:
                    failures.append("transaction was not read-only")
                if response.search.database_role != settings.copilot_execution_role:
                    failures.append(
                        f"database_role={response.search.database_role}"
                    )
                if response.search.match_count == 0:
                    failures.append("no vector matches returned")

                if case.get("expect_open_parks_only"):
                    if any(
                        match.metadata.get("current_status") != "Open"
                        for match in response.search.matches
                    ):
                        failures.append("non-open park returned")

                expected_level = case.get("expected_education_level_code")
                if expected_level and any(
                    match.metadata.get("education_level_code") != expected_level
                    for match in response.search.matches
                ):
                    failures.append("education-level filter was not honored")

                expected_terms = case.get("expected_title_terms_any")
                if expected_terms and not _contains_any(
                    [match.title for match in response.search.matches],
                    expected_terms,
                ):
                    failures.append(
                        f"none of the top titles contained {expected_terms}"
                    )
            else:
                expected_status = case.get("expected_status")
                if expected_status and response.status.value != expected_status:
                    failures.append(
                        f"status={response.status.value}, expected={expected_status}"
                    )

            passed = not failures
            passed_count += int(passed)
            results.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "route": response.route.value,
                    "status": response.status.value,
                    "match_count": (
                        response.search.match_count if response.search else 0
                    ),
                    "top_titles": (
                        [match.title for match in response.search.matches[:5]]
                        if response.search
                        else []
                    ),
                    "passed": passed,
                    "failures": failures,
                }
            )
            label = "PASS" if passed else "FAIL"
            print(
                f"{label} {case['id']}: {response.route.value} / "
                f"{results[-1]['match_count']} matches"
            )
            for failure in failures:
                print(f"  - {failure}")
    finally:
        try:
            connection.rollback()
        finally:
            connection.close()

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "benchmark": benchmark["benchmark"],
        "embedding_model": settings.embedding_model_name,
        "passed": passed_count,
        "total": len(results),
        "pass_rate": round(passed_count / len(results), 4),
        "cases": results,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"\nVector benchmark: {passed_count}/{len(results)} passed "
        f"({100 * passed_count / len(results):.1f}%)"
    )
    if passed_count != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
