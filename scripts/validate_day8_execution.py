"""Live Day 8 execution benchmark against PostgreSQL/PostGIS."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.schema_catalog import build_static_catalog
from app.copilot.sql_execution import CopilotExecutionService, ReadOnlySQLExecutor
from app.copilot.sql_generator import TemplateSQLGenerator
from app.copilot.sql_validator import SQLASTValidator
from app.db.connection import open_db_connection

CASES_PATH = PROJECT_ROOT / "benchmarks/day8/validation_execution_cases.json"
OUTPUT_PATH = PROJECT_ROOT / "results/day8/execution_validation.json"


def execute_case(question: str):
    settings = get_settings()
    catalog = build_static_catalog()
    generator = TemplateSQLGenerator(RuleBasedQueryPlanner(catalog))
    validator = SQLASTValidator(
        catalog,
        max_result_rows=settings.copilot_max_result_rows,
    )
    connection = open_db_connection(settings)
    try:
        connection.execute("SET TRANSACTION READ ONLY")
        connection.execute(
            "SELECT set_config('statement_timeout', %s, true)",
            (str(settings.copilot_execution_timeout_ms),),
        )
        service = CopilotExecutionService(
            generator,
            validator,
            ReadOnlySQLExecutor(connection, settings),
            settings,
        )
        return service.execute(question)
    finally:
        try:
            connection.rollback()
        finally:
            connection.close()


def main() -> None:
    benchmark = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    records: list[dict] = []
    passed = 0

    for case in benchmark["cases"]:
        response = execute_case(case["question"])
        checks = {
            "intent": response.generation.intent.value == case["expected_intent"],
            "status": response.status.value == case["expected_execution_status"],
            "row_count": response.row_count == case["expected_row_count"],
            "read_only": (
                response.transaction_read_only
                if response.status.value == "executed"
                else True
            ),
            "restricted_role": (
                response.database_role == "agenticdb_reader"
                if response.status.value == "executed"
                else True
            ),
        }
        case_passed = all(checks.values())
        passed += int(case_passed)
        print(
            f"{'PASS' if case_passed else 'FAIL'} {case['id']}: "
            f"{response.status.value} / {response.row_count} rows / "
            f"{response.elapsed_ms if response.elapsed_ms is not None else '-'} ms"
        )
        records.append(
            {
                "id": case["id"],
                "question": case["question"],
                "intent": response.generation.intent.value,
                "status": response.status.value,
                "row_count": response.row_count,
                "elapsed_ms": response.elapsed_ms,
                "database_role": response.database_role,
                "transaction_read_only": response.transaction_read_only,
                "query_fingerprint": response.validation.query_fingerprint,
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
    print(
        f"\nRead-only execution benchmark: "
        f"{passed}/{total} passed ({passed / total:.1%})"
    )
    print(f"Report: {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
