#!/usr/bin/env python3
"""Run the live OpenAI-assisted planning and execution benchmark."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.config import get_settings
from app.copilot.agent_orchestrator import LazyReadOnlySQLExecutor
from app.copilot.answer_synthesis import DeterministicAnswerSynthesizer
from app.copilot.llm_orchestrator import LLMAssistedAgentOrchestrator
from app.copilot.llm_planner import LLMAssistedPlanningService
from app.copilot.llm_provider import OpenAIResponsesPlanningProvider
from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.schema_catalog import build_static_catalog
from app.copilot.sql_generator import TemplateSQLGenerator
from app.copilot.sql_validator import SQLASTValidator
from app.models.llm import RequestedPlanningProvider


BENCHMARK_PATH = Path("benchmarks/day11/llm_cases.json")
OUTPUT_PATH = Path("results/day11/llm_validation.json")


def main() -> None:
    settings = get_settings()
    if not settings.openai_api_key_configured:
        raise SystemExit(
            "OPENAI_API_KEY is not configured in .env; the live Day 11 "
            "benchmark requires a hosted-model call."
        )

    benchmark = json.loads(BENCHMARK_PATH.read_text())
    catalog = build_static_catalog()
    deterministic = RuleBasedQueryPlanner(catalog)
    provider = OpenAIResponsesPlanningProvider(
        api_key=settings.openai_api_key_value,
        model=settings.openai_llm_model,
        timeout_seconds=settings.openai_llm_timeout_seconds,
        max_output_tokens=settings.openai_llm_max_output_tokens,
        input_cost_per_million=settings.openai_input_cost_per_million,
        output_cost_per_million=settings.openai_output_cost_per_million,
    )
    planning_service = LLMAssistedPlanningService(
        deterministic,
        catalog,
        provider=provider,
        default_provider="openai",
        fallback_to_deterministic=False,
    )
    orchestrator = LLMAssistedAgentOrchestrator(
        planning_service=planning_service,
        generator=TemplateSQLGenerator(deterministic),
        validator=SQLASTValidator(
            catalog,
            max_result_rows=settings.copilot_max_result_rows,
        ),
        executor=LazyReadOnlySQLExecutor(settings),
        synthesizer=DeterministicAnswerSynthesizer(),
        settings=settings,
    )

    results: list[dict] = []
    passed_count = 0
    llm_intent_correct = 0
    deterministic_intent_correct = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0
    cost_available = False

    for case in benchmark["cases"]:
        baseline = deterministic.plan(case["question"]).plan
        deterministic_correct = baseline.intent.value == case["expected_intent"]
        deterministic_intent_correct += int(deterministic_correct)

        response = orchestrator.run(
            case["question"],
            requested_provider=RequestedPlanningProvider.openai,
            evidence_limit=3,
        )
        planning = response.planning
        run = response.run
        intent_correct = run.intent.value == case["expected_intent"]
        status_correct = run.status.value == case["expected_status"]
        row_count = run.execution.row_count if run.execution is not None else 0
        rows_correct = row_count == case["expected_rows"]
        no_fallback = planning.fallback_used is False
        provider_correct = (
            planning.provider_used == "local_safety_gate"
            if case["expected_intent"] == "unsafe_request"
            else planning.provider_used == "openai"
        )
        case_passed = all(
            [intent_correct, status_correct, rows_correct, no_fallback, provider_correct]
        )
        passed_count += int(case_passed)
        llm_intent_correct += int(intent_correct)

        usage = planning.usage
        total_input_tokens += usage.input_tokens
        total_output_tokens += usage.output_tokens
        if usage.estimated_cost_usd is not None:
            total_cost += usage.estimated_cost_usd
            cost_available = True

        result = {
            "id": case["id"],
            "question": case["question"],
            "expected_intent": case["expected_intent"],
            "actual_intent": run.intent.value,
            "expected_status": case["expected_status"],
            "actual_status": run.status.value,
            "expected_rows": case["expected_rows"],
            "actual_rows": row_count,
            "provider_used": planning.provider_used,
            "fallback_used": planning.fallback_used,
            "model": planning.model,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "llm_elapsed_ms": usage.elapsed_ms,
            "total_elapsed_ms": response.total_elapsed_ms,
            "estimated_cost_usd": usage.estimated_cost_usd,
            "deterministic_baseline_intent": baseline.intent.value,
            "deterministic_baseline_correct": deterministic_correct,
            "passed": case_passed,
        }
        results.append(result)
        label = "PASS" if case_passed else "FAIL"
        print(
            f"{label} {case['id']}: {run.intent.value} / {run.status.value} / "
            f"{row_count} rows / provider={planning.provider_used}"
        )
        if not case_passed:
            print(
                "  expected "
                f"intent={case['expected_intent']} status={case['expected_status']} "
                f"rows={case['expected_rows']}"
            )

    total_cases = len(results)
    summary = {
        "benchmark_name": benchmark["benchmark_name"],
        "model": settings.openai_llm_model,
        "cases": total_cases,
        "passed": passed_count,
        "pass_rate": round(passed_count / total_cases, 4),
        "llm_intent_accuracy": round(llm_intent_correct / total_cases, 4),
        "deterministic_intent_accuracy": round(
            deterministic_intent_correct / total_cases,
            4,
        ),
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "estimated_cost_usd": round(total_cost, 8) if cost_available else None,
        "results": results,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(summary, indent=2) + "\n")

    print()
    print(
        f"Day 11 OpenAI benchmark: {passed_count}/{total_cases} passed "
        f"({summary['pass_rate'] * 100:.1f}%)"
    )
    print(f"LLM intent accuracy: {summary['llm_intent_accuracy'] * 100:.1f}%")
    print(
        "Deterministic intent accuracy on the same wording: "
        f"{summary['deterministic_intent_accuracy'] * 100:.1f}%"
    )
    print(
        f"Tokens: {total_input_tokens} input / {total_output_tokens} output"
    )
    if cost_available:
        print(f"Estimated cost: ${summary['estimated_cost_usd']:.8f}")

    if passed_count != total_cases:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
