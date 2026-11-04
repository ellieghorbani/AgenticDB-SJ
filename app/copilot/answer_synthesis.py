"""Deterministic evidence-backed answer synthesis for Day 9."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.models.agent import AgentAnswer, AgentEvidenceRow
from app.models.copilot import PlannerIntent, QueryPlan


def _display(value: Any) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


class DeterministicAnswerSynthesizer:
    """Summarize only the rows returned by the controlled executor."""

    synthesizer_name = "deterministic_answer_day9"

    def synthesize(
        self,
        plan: QueryPlan,
        rows: list[dict[str, Any]],
        *,
        sources: list[str],
        query_fingerprint: str | None,
        evidence_limit: int,
    ) -> AgentAnswer:
        row_count = len(rows)
        evidence = [
            AgentEvidenceRow(row_number=index + 1, values=dict(row))
            for index, row in enumerate(rows[:evidence_limit])
        ]
        text = self._answer_text(plan.intent, rows)
        return AgentAnswer(
            text=text,
            row_count=row_count,
            evidence=evidence,
            evidence_limited=row_count > len(evidence),
            sources=sorted(set(sources)),
            query_fingerprint=query_fingerprint,
        )

    def blocked_answer(self, plan: QueryPlan) -> AgentAnswer:
        if plan.intent == PlannerIntent.unsafe_request:
            text = (
                "The request was blocked because AgenticDB-SJ permits read-only "
                "questions and does not perform destructive database actions."
            )
        elif plan.requires_clarification:
            text = (
                "The request needs clarification before SQL can be generated; provide "
                "the missing entity or location name."
            )
        else:
            text = (
                "The question is outside the datasets and query patterns currently "
                "supported by AgenticDB-SJ."
            )
        return AgentAnswer(text=text, row_count=0)

    def _answer_text(
        self,
        intent: PlannerIntent,
        rows: list[dict[str, Any]],
    ) -> str:
        if not rows:
            return "No database rows matched the validated query."

        first = rows[0]
        row_count = len(rows)

        if intent == PlannerIntent.schools_per_neighborhood:
            top_count = first.get("active_school_count")
            tied = [
                str(row.get("neighborhood_name"))
                for row in rows
                if row.get("active_school_count") == top_count
            ][:3]
            return (
                f"The query returned {row_count} neighborhoods. "
                f"The highest active-school count is {_display(top_count)}, "
                f"reported for {', '.join(tied)}."
            )

        if intent == PlannerIntent.open_parks_per_neighborhood:
            return (
                f"The query returned {row_count} neighborhoods. "
                f"{first.get('neighborhood_name')} has the highest listed open "
                f"park-feature count ({_display(first.get('open_park_feature_count'))})."
            )

        if intent == PlannerIntent.elementary_schools_near_open_parks:
            return (
                f"Found {row_count} active elementary schools within the requested "
                f"distance of an open park feature. The closest listed match is "
                f"{first.get('school_name')} to {first.get('nearest_open_park_name')} "
                f"at {_display(first.get('distance_miles'))} miles."
            )

        if intent == PlannerIntent.nearest_open_park_per_school:
            return (
                f"Identified the nearest open park feature for {row_count} active "
                f"schools. The closest listed pair is {first.get('school_name')} and "
                f"{first.get('nearest_open_park_name')} at "
                f"{_display(first.get('distance_miles'))} miles."
            )

        if intent == PlannerIntent.open_parks_intersecting_neighborhood:
            return (
                f"Found {row_count} open park features intersecting "
                f"{first.get('neighborhood_name')}."
            )

        if intent == PlannerIntent.neighborhoods_with_minimum_schools_and_parks:
            return (
                f"Found {row_count} neighborhoods meeting both thresholds. "
                f"The first ranked result is {first.get('neighborhood_name')} with "
                f"{_display(first.get('active_school_count'))} active schools and "
                f"{_display(first.get('open_park_feature_count'))} open park features."
            )

        if intent == PlannerIntent.average_nearest_park_distance_by_neighborhood:
            return (
                f"Computed nearest-open-park distance statistics for {row_count} "
                f"neighborhoods. The first ranked result is "
                f"{first.get('neighborhood_name')} with an average of "
                f"{_display(first.get('average_nearest_park_distance_m'))} meters."
            )

        if intent == PlannerIntent.open_parks_with_most_nearby_schools:
            return (
                f"Ranked {row_count} open park features by nearby active schools. "
                f"{first.get('park_name')} has the highest listed count "
                f"({_display(first.get('active_school_count_within_one_mile'))})."
            )

        if intent == PlannerIntent.neighborhoods_with_elementary_and_high_schools:
            return (
                f"Found {row_count} neighborhoods containing both elementary and "
                f"high-school records. The first ranked result is "
                f"{first.get('neighborhood_name')} with "
                f"{_display(first.get('elementary_school_count'))} elementary and "
                f"{_display(first.get('high_school_count'))} high-school records."
            )

        return f"The validated query returned {row_count} database rows."
