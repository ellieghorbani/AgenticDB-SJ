#!/usr/bin/env python3
"""Run the deterministic Day 6 planner benchmark and save a JSON report."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.schema_catalog import build_static_catalog


BENCHMARK_PATH = PROJECT_ROOT / "benchmarks/day6/planner_cases.json"
OUTPUT_PATH = PROJECT_ROOT / "results/day6/planner_validation.json"


def main() -> None:
    benchmark = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    planner = RuleBasedQueryPlanner(build_static_catalog())

    results = []
    passed = 0
    for case in benchmark["cases"]:
        response = planner.plan(case["question"])
        actual_relations = set(response.plan.relations)
        expected_relations = set(case["required_relations"])
        checks = {
            "intent": response.plan.intent.value == case["expected_intent"],
            "query_type": response.plan.query_type.value == case["expected_query_type"],
            "required_relations": expected_relations.issubset(actual_relations),
            "execution_disabled": response.plan.execution_allowed is False,
            "sql_not_generated": response.plan.sql_generated is False,
        }
        case_passed = all(checks.values())
        passed += int(case_passed)
        results.append(
            {
                "id": case["id"],
                "question": case["question"],
                "expected_intent": case["expected_intent"],
                "actual_intent": response.plan.intent.value,
                "expected_query_type": case["expected_query_type"],
                "actual_query_type": response.plan.query_type.value,
                "expected_required_relations": sorted(expected_relations),
                "actual_relations": response.plan.relations,
                "checks": checks,
                "passed": case_passed,
            }
        )

    total = len(results)
    report = {
        "benchmark_name": benchmark["benchmark_name"],
        "planner": benchmark["planner"],
        "cases": total,
        "passed": passed,
        "accuracy": round(passed / total, 4) if total else 0.0,
        "all_execution_disabled": all(
            result["checks"]["execution_disabled"] for result in results
        ),
        "all_sql_not_generated": all(
            result["checks"]["sql_not_generated"] for result in results
        ),
        "results": results,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    for result in results:
        marker = "PASS" if result["passed"] else "FAIL"
        print(
            f"{marker} {result['id']}: "
            f"{result['actual_intent']} / {result['actual_query_type']}"
        )
    print(f"\nPlanner benchmark: {passed}/{total} passed ({report['accuracy']:.1%})")
    print(f"Report: {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
