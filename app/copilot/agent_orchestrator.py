"""Day 9 deterministic agent router and traced tool workflow."""

from __future__ import annotations

from time import perf_counter
from typing import Any
from uuid import uuid4

from app.core.config import Settings
from app.copilot.answer_synthesis import DeterministicAnswerSynthesizer
from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.sql_execution import ReadOnlySQLExecutor
from app.copilot.sql_generator import TemplateSQLGenerator
from app.copilot.sql_validator import SQLASTValidator
from app.db.connection import open_db_connection
from app.models.agent import (
    AgentExecutionSummary,
    AgentRoute,
    AgentRunResponse,
    AgentRunStatus,
    AgentToolName,
    AgentToolTrace,
    ToolCallStatus,
)
from app.models.copilot import PlannerIntent, QueryPlan, QueryType
from app.models.sql_generation import SQLGenerationStatus


class LazyReadOnlySQLExecutor:
    """Open PostgreSQL only when the agent reaches the execution tool."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def execute(self, sql_text: str, parameters: tuple[Any, ...]):
        connection = open_db_connection(self.settings)
        try:
            connection.execute("SET TRANSACTION READ ONLY")
            return ReadOnlySQLExecutor(connection, self.settings).execute(
                sql_text,
                parameters,
            )
        finally:
            try:
                connection.rollback()
            finally:
                connection.close()


class DeterministicAgentRouter:
    """Choose the Day 9 route from a validated typed plan."""

    def route(self, plan: QueryPlan) -> AgentRoute:
        if plan.intent == PlannerIntent.unsafe_request:
            return AgentRoute.blocked
        if plan.intent == PlannerIntent.unsupported:
            return AgentRoute.unsupported
        if plan.requires_clarification:
            return AgentRoute.requires_clarification
        return AgentRoute.relational_sql


class AgentOrchestrator:
    """Run the approved tool chain and preserve an auditable trace."""

    agent_name = "deterministic_agent_day9"

    def __init__(
        self,
        planner: RuleBasedQueryPlanner,
        generator: TemplateSQLGenerator,
        validator: SQLASTValidator,
        executor: ReadOnlySQLExecutor,
        synthesizer: DeterministicAnswerSynthesizer,
        settings: Settings,
    ):
        self.planner = planner
        self.generator = generator
        self.validator = validator
        self.executor = executor
        self.synthesizer = synthesizer
        self.settings = settings
        self.router = DeterministicAgentRouter()

    def run(
        self,
        question: str,
        *,
        top_k: int = 6,
        evidence_limit: int = 5,
    ) -> AgentRunResponse:
        run_started = perf_counter()
        trace: list[AgentToolTrace] = []

        started = perf_counter()
        plan_response = self.planner.plan(question, top_k=top_k)
        plan = plan_response.plan
        trace.append(
            self._trace(
                1,
                AgentToolName.query_plan,
                ToolCallStatus.succeeded,
                started,
                {"question_length": len(question), "top_k": top_k},
                {
                    "intent": plan.intent.value,
                    "query_type": plan.query_type.value,
                    "relation_count": len(plan.relations),
                    "requires_clarification": plan.requires_clarification,
                },
                "Created a typed plan using allowlisted schema context.",
            )
        )

        started = perf_counter()
        route = self.router.route(plan)
        route_status = (
            ToolCallStatus.succeeded
            if route == AgentRoute.relational_sql
            else ToolCallStatus.blocked
        )
        trace.append(
            self._trace(
                2,
                AgentToolName.route_select,
                route_status,
                started,
                {"intent": plan.intent.value, "query_type": plan.query_type.value},
                {"route": route.value},
                (
                    "Selected the controlled relational/spatial SQL workflow."
                    if route == AgentRoute.relational_sql
                    else "Stopped before SQL generation because the route is not executable."
                ),
            )
        )

        if route != AgentRoute.relational_sql:
            for sequence, tool in enumerate(
                [
                    AgentToolName.sql_generate,
                    AgentToolName.sql_validate,
                    AgentToolName.sql_execute,
                ],
                start=3,
            ):
                trace.append(
                    AgentToolTrace(
                        sequence=sequence,
                        tool=tool,
                        status=ToolCallStatus.skipped,
                        elapsed_ms=0.0,
                        message="Skipped because routing did not grant an executable path.",
                    )
                )
            started = perf_counter()
            answer = self.synthesizer.blocked_answer(plan)
            trace.append(
                self._trace(
                    6,
                    AgentToolName.answer_synthesize,
                    ToolCallStatus.succeeded,
                    started,
                    {"route": route.value},
                    {"row_count": 0, "evidence_count": 0},
                    "Created a safe non-executing response.",
                )
            )
            status = (
                AgentRunStatus.requires_clarification
                if route == AgentRoute.requires_clarification
                else AgentRunStatus.blocked
            )
            return AgentRunResponse(
                run_id=str(uuid4()),
                status=status,
                route=route,
                question=plan.question,
                intent=plan.intent,
                query_type=plan.query_type,
                plan=plan,
                answer=answer,
                tool_trace=trace,
                warnings=list(plan.warnings),
                total_elapsed_ms=self._elapsed(run_started),
                execution_allowed=False,
            )

        started = perf_counter()
        generation = self.generator.generate_from_plan(plan)
        generation_ok = generation.status == SQLGenerationStatus.generated
        trace.append(
            self._trace(
                3,
                AgentToolName.sql_generate,
                ToolCallStatus.succeeded if generation_ok else ToolCallStatus.blocked,
                started,
                {"intent": plan.intent.value},
                {
                    "status": generation.status.value,
                    "sql_generated": generation.sql_generated,
                    "parameter_count": len(generation.parameters),
                },
                "Generated reviewed parameterized SQL." if generation_ok else "SQL generation was blocked.",
            )
        )

        started = perf_counter()
        validation = self.validator.validate(generation)
        validation_ok = validation.execution_allowed
        trace.append(
            self._trace(
                4,
                AgentToolName.sql_validate,
                ToolCallStatus.succeeded if validation_ok else ToolCallStatus.blocked,
                started,
                {"generator_status": generation.status.value},
                {
                    "status": validation.status.value,
                    "execution_allowed": validation.execution_allowed,
                    "query_fingerprint": validation.query_fingerprint,
                },
                "Independent AST policy granted execution." if validation_ok else "Independent AST policy blocked execution.",
            )
        )

        if not generation_ok or not validation_ok or generation.sql is None:
            trace.append(
                AgentToolTrace(
                    sequence=5,
                    tool=AgentToolName.sql_execute,
                    status=ToolCallStatus.skipped,
                    elapsed_ms=0.0,
                    message="Skipped because SQL did not receive validation permission.",
                )
            )
            started = perf_counter()
            answer = self.synthesizer.blocked_answer(plan)
            trace.append(
                self._trace(
                    6,
                    AgentToolName.answer_synthesize,
                    ToolCallStatus.succeeded,
                    started,
                    {"validation_status": validation.status.value},
                    {"row_count": 0, "evidence_count": 0},
                    "Created a safe non-executing response.",
                )
            )
            return AgentRunResponse(
                run_id=str(uuid4()),
                status=AgentRunStatus.blocked,
                route=route,
                question=plan.question,
                intent=plan.intent,
                query_type=plan.query_type,
                plan=plan,
                generation=generation,
                validation=validation,
                answer=answer,
                tool_trace=trace,
                warnings=[*generation.warnings, *validation.warnings],
                total_elapsed_ms=self._elapsed(run_started),
                execution_allowed=False,
            )

        parameters = tuple(parameter.value for parameter in generation.parameters)
        started = perf_counter()
        result = self.executor.execute(generation.sql, parameters)
        trace.append(
            self._trace(
                5,
                AgentToolName.sql_execute,
                ToolCallStatus.succeeded,
                started,
                {
                    "query_fingerprint": validation.query_fingerprint,
                    "parameter_count": len(parameters),
                },
                {
                    "row_count": len(result.rows),
                    "truncated": result.truncated,
                    "database_role": result.database_role,
                    "transaction_read_only": result.transaction_read_only,
                },
                "Executed validated SQL under the restricted read-only role.",
            )
        )

        started = perf_counter()
        answer = self.synthesizer.synthesize(
            plan,
            result.rows,
            sources=generation.relations,
            query_fingerprint=validation.query_fingerprint,
            evidence_limit=evidence_limit,
        )
        trace.append(
            self._trace(
                6,
                AgentToolName.answer_synthesize,
                ToolCallStatus.succeeded,
                started,
                {"row_count": len(result.rows), "evidence_limit": evidence_limit},
                {
                    "evidence_count": len(answer.evidence),
                    "evidence_limited": answer.evidence_limited,
                },
                "Synthesized an answer using only returned database rows.",
            )
        )

        warnings = [*generation.warnings, *validation.warnings]
        if result.truncated:
            warnings.append(
                f"Results were truncated to {self.settings.copilot_max_result_rows} rows."
            )
        execution = AgentExecutionSummary(
            row_count=len(result.rows),
            columns=result.columns,
            truncated=result.truncated,
            elapsed_ms=result.elapsed_ms,
            database_role=result.database_role,
            transaction_read_only=result.transaction_read_only,
            statement_timeout_ms=self.settings.copilot_execution_timeout_ms,
            query_fingerprint=validation.query_fingerprint or "",
        )
        return AgentRunResponse(
            run_id=str(uuid4()),
            status=AgentRunStatus.completed,
            route=route,
            question=plan.question,
            intent=plan.intent,
            query_type=plan.query_type,
            plan=plan,
            generation=generation,
            validation=validation,
            execution=execution,
            answer=answer,
            tool_trace=trace,
            warnings=warnings,
            total_elapsed_ms=self._elapsed(run_started),
            execution_allowed=True,
        )

    @staticmethod
    def _elapsed(started: float) -> float:
        return round((perf_counter() - started) * 1000.0, 3)

    def _trace(
        self,
        sequence: int,
        tool: AgentToolName,
        status: ToolCallStatus,
        started: float,
        input_summary: dict[str, Any],
        output_summary: dict[str, Any],
        message: str,
    ) -> AgentToolTrace:
        return AgentToolTrace(
            sequence=sequence,
            tool=tool,
            status=status,
            elapsed_ms=self._elapsed(started),
            input_summary=input_summary,
            output_summary=output_summary,
            message=message,
        )
