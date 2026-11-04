"""Live Day 9 benchmark for routing, tool use, evidence, and execution."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from app.copilot.agent_orchestrator import AgentOrchestrator, LazyReadOnlySQLExecutor
from app.copilot.answer_synthesis import DeterministicAnswerSynthesizer
from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.schema_catalog import build_static_catalog
from app.copilot.sql_generator import TemplateSQLGenerator
from app.copilot.sql_validator import SQLASTValidator

CASES_PATH = PROJECT_ROOT / "benchmarks/day9/agent_cases.json"
OUTPUT_PATH = PROJECT_ROOT / "results/day9/agent_validation.json"


def run_case(question: str):
    settings = get_settings()
    catalog = build_static_catalog()
    planner = RuleBasedQueryPlanner(catalog)
    orchestrator = AgentOrchestrator(
        planner=planner,
        generator=TemplateSQLGenerator(planner),
        validator=SQLASTValidator(
            catalog,
            max_result_rows=settings.copilot_max_result_rows,
        ),
        executor=LazyReadOnlySQLExecutor(settings),
        synthesizer=DeterministicAnswerSynthesizer(),
        settings=settings,
    )
    return orchestrator.run(question, evidence_limit=5)


def main() -> None:
    benchmark = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    expected_tools = benchmark["expected_tool_sequence"]
    records: list[dict] = []
    passed = 0

    for case in benchmark["cases"]:
        response = run_case(case["question"])
        tool_names = [item.tool.value for item in response.tool_trace]
        tool_statuses = [item.status.value for item in response.tool_trace]
        completed = response.status.value == "completed"
        checks = {
            "intent": response.intent.value == case["expected_intent"],
            "route": response.route.value == case["expected_route"],
            "status": response.status.value == case["expected_status"],
            "row_count": response.answer.row_count == case["expected_row_count"],
            "tool_sequence": tool_names == expected_tools,
            "evidence_bounded": len(response.answer.evidence) <= 5,
            "answer_present": bool(response.answer.text.strip()),
            "read_only": (
                response.execution.transaction_read_only
                if completed and response.execution is not None
                else True
            ),
            "restricted_role": (
                response.execution.database_role == "agenticdb_reader"
                if completed and response.execution is not None
                else True
            ),
            "fingerprint": (
                bool(response.answer.query_fingerprint) if completed else True
            ),
            "blocked_tools_skipped": (
                tool_statuses[2:5] == ["skipped", "skipped", "skipped"]
                if not completed
                else all(status == "succeeded" for status in tool_statuses)
            ),
        }
        case_passed = all(checks.values())
        passed += int(case_passed)
        print(
            f"{'PASS' if case_passed else 'FAIL'} {case['id']}: "
            f"{response.route.value} / {response.status.value} / "
            f"{response.answer.row_count} rows / {response.total_elapsed_ms} ms"
        )
        records.append(
            {
                "id": case["id"],
                "question": case["question"],
                "intent": response.intent.value,
                "route": response.route.value,
                "status": response.status.value,
                "row_count": response.answer.row_count,
                "evidence_count": len(response.answer.evidence),
                "tool_names": tool_names,
                "tool_statuses": tool_statuses,
                "total_elapsed_ms": response.total_elapsed_ms,
                "execution_elapsed_ms": (
                    response.execution.elapsed_ms if response.execution else None
                ),
                "query_fingerprint": response.answer.query_fingerprint,
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
    print(f"\nAgent workflow benchmark: {passed}/{total} passed ({passed / total:.1%})")
    print(f"Report: {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
