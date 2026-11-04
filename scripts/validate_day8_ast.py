"""Offline Day 8 AST-validation benchmark, including adversarial SQL."""

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
from app.copilot.sql_validator import SQLASTValidator

CASES_PATH = PROJECT_ROOT / "benchmarks/day8/validation_execution_cases.json"
OUTPUT_PATH = PROJECT_ROOT / "results/day8/ast_validation.json"


def main() -> None:
    benchmark = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    catalog = build_static_catalog()
    generator = TemplateSQLGenerator(RuleBasedQueryPlanner(catalog))
    validator = SQLASTValidator(catalog, max_result_rows=1000)

    records: list[dict] = []
    passed = 0

    for case in benchmark["cases"]:
        generation = generator.generate(case["question"])
        validation = validator.validate(generation)
        expected_valid = case["expected_execution_status"] == "executed"
        checks = {
            "intent": generation.intent.value == case["expected_intent"],
            "validation_status": (
                validation.status.value == "valid"
                if expected_valid
                else validation.status.value in {"blocked", "not_generated"}
            ),
            "execution_policy": validation.execution_allowed is expected_valid,
            "all_checks": (
                all(check.passed for check in validation.checks)
                if expected_valid
                else True
            ),
        }
        case_passed = all(checks.values())
        passed += int(case_passed)
        print(
            f"{'PASS' if case_passed else 'FAIL'} {case['id']}: "
            f"{generation.intent.value} / {validation.status.value}"
        )
        records.append(
            {
                "id": case["id"],
                "kind": "question",
                "intent": generation.intent.value,
                "validation_status": validation.status.value,
                "execution_allowed": validation.execution_allowed,
                "checks": checks,
                "passed": case_passed,
            }
        )

    base_generation = generator.generate(
        "How many active public schools are located in each neighborhood?"
    )
    for attack in benchmark["adversarial_sql"]:
        statement_type = (
            "WITH" if attack["sql"].lstrip().lower().startswith("with") else "SELECT"
        )
        tampered = base_generation.model_copy(
            update={
                "sql": attack["sql"],
                "statement_type": statement_type,
                "sql_generated": True,
            }
        )
        validation = validator.validate(tampered)
        check_lookup = {check.name: check.passed for check in validation.checks}
        expected_check = attack["expected_failed_check"]
        checks = {
            "blocked": validation.execution_allowed is False,
            "status": validation.status.value == "blocked",
            "expected_check_failed": check_lookup.get(expected_check) is False,
        }
        case_passed = all(checks.values())
        passed += int(case_passed)
        print(
            f"{'PASS' if case_passed else 'FAIL'} {attack['id']}: "
            f"blocked by {expected_check}"
        )
        records.append(
            {
                "id": attack["id"],
                "kind": "adversarial_sql",
                "validation_status": validation.status.value,
                "expected_failed_check": expected_check,
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

    print(f"\nAST validation benchmark: {passed}/{total} passed ({passed / total:.1%})")
    print(f"Report: {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
