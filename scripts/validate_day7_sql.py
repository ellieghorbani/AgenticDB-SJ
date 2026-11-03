"""Offline validation for Day 7 deterministic SQL generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.schema_catalog import build_static_catalog
from app.copilot.sql_generator import TemplateSQLGenerator

ROOT = PROJECT_ROOT
CASES_PATH = ROOT / "benchmarks/day7/sql_generation_cases.json"
OUTPUT_PATH = ROOT / "results/day7/sql_generation_validation.json"


def main() -> None:
    benchmark = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    generator = TemplateSQLGenerator(RuleBasedQueryPlanner(build_static_catalog()))
    records: list[dict] = []
    passed = 0

    for case in benchmark["cases"]:
        response = generator.generate(case["question"])
        parameter_values = [parameter.value for parameter in response.parameters]
        checks = {
            "intent": response.intent.value == case["expected_intent"],
            "status": response.status.value == case["expected_status"],
            "relations": set(case["required_relations"]).issubset(response.relations),
            "parameters": parameter_values == case["expected_parameter_values"],
            "execution_disabled": response.execution_allowed is False,
        }

        if response.status.value == "generated":
            checks.update(
                {
                    "sql_present": bool(response.sql),
                    "sql_generated": response.sql_generated is True,
                    "all_safety_checks": all(
                        safety_check.passed
                        for safety_check in response.safety_checks
                    ),
                    "placeholder_count": (
                        response.sql.count("%s") == len(response.parameters)
                        if response.sql
                        else False
                    ),
                }
            )
        else:
            checks.update(
                {
                    "sql_absent": response.sql is None,
                    "sql_not_generated": response.sql_generated is False,
                    "parameters_absent": not response.parameters,
                }
            )

        case_passed = all(checks.values())
        passed += int(case_passed)
        print(
            f"{'PASS' if case_passed else 'FAIL'} {case['id']}: "
            f"{response.intent.value} / {response.status.value}"
        )
        records.append(
            {
                "id": case["id"],
                "question": case["question"],
                "intent": response.intent.value,
                "status": response.status.value,
                "relations": response.relations,
                "parameter_values": parameter_values,
                "checks": checks,
                "passed": case_passed,
            }
        )

    total = len(records)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(
            {
                "benchmark": benchmark["benchmark_name"],
                "passed": passed,
                "total": total,
                "accuracy": passed / total if total else 0,
                "cases": records,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"\nSQL generation benchmark: {passed}/{total} passed ({passed / total:.1%})")
    print(f"Report: {OUTPUT_PATH.relative_to(ROOT)}")
    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
