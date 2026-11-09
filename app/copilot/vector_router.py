"""Deterministic natural-language router for Day 10 vector retrieval."""

from __future__ import annotations

import re

from app.models.vector import (
    VectorEntityType,
    VectorRoute,
    VectorRouteDecision,
)


_UNSAFE_WORDS = {
    "delete",
    "drop",
    "update",
    "insert",
    "alter",
    "truncate",
    "create",
    "grant",
    "revoke",
    "vacuum",
    "copy",
}

_SEMANTIC_CUES = (
    "related to",
    "similar to",
    "about",
    "conceptually",
    "semantic",
    "matching",
    "relevant to",
)


class DeterministicVectorRouter:
    """Map supported questions to semantic or hybrid-vector search."""

    router_name = "deterministic_vector_router_day10"

    def route(
        self,
        question: str,
        *,
        top_k: int = 5,
        min_similarity: float = 0.20,
    ) -> VectorRouteDecision:
        normalized = " ".join(question.strip().split())
        lower = normalized.lower()

        if any(
            re.search(rf"\b{word}\b", lower)
            for word in _UNSAFE_WORDS
        ):
            return VectorRouteDecision(
                question=normalized,
                route=VectorRoute.blocked,
                query_text=normalized,
                top_k=top_k,
                min_similarity=min_similarity,
                reason=(
                    "The question contains a destructive database action."
                ),
                execution_allowed=False,
            )

        entity_types = self._entity_types(lower)
        has_semantic_cue = any(
            cue in lower for cue in _SEMANTIC_CUES
        )

        if not entity_types or not has_semantic_cue:
            return VectorRouteDecision(
                question=normalized,
                route=VectorRoute.unsupported,
                query_text=normalized,
                top_k=top_k,
                min_similarity=min_similarity,
                reason=(
                    "Day 10 vector routing requires a supported entity "
                    "(park, school, or neighborhood) and a semantic cue "
                    "such as 'related to' or 'similar to'."
                ),
                execution_allowed=False,
            )

        only_open_parks = (
            VectorEntityType.park in entity_types
            and "open" in lower
        )

        education_level_code = None
        if VectorEntityType.school in entity_types:
            if "elementary" in lower:
                education_level_code = "ELEM"
            elif (
                "high school" in lower
                or "high-school" in lower
            ):
                education_level_code = "HS"

        route = (
            VectorRoute.hybrid_vector
            if only_open_parks
            or education_level_code is not None
            else VectorRoute.semantic_vector
        )

        return VectorRouteDecision(
            question=normalized,
            route=route,
            query_text=normalized,
            entity_types=entity_types,
            only_open_parks=only_open_parks,
            education_level_code=education_level_code,
            top_k=top_k,
            min_similarity=min_similarity,
            reason=(
                "Selected semantic similarity with structured "
                "metadata filters."
                if route == VectorRoute.hybrid_vector
                else (
                    "Selected semantic similarity over the "
                    "supported entity types."
                )
            ),
            execution_allowed=True,
        )

    @staticmethod
    def _entity_types(
        question: str,
    ) -> list[VectorEntityType]:
        """Return requested entity types.

        Explicit entity nouns take precedence over fallback aliases.
        This prevents a proper name such as ``Rose Garden`` from
        being incorrectly treated as a park request when the user
        explicitly asks for neighborhoods.
        """

        selected: list[VectorEntityType] = []

        # First recognize explicit supported entity nouns.
        if re.search(
            r"\bparks?\b|\bpark[ -]?features?\b",
            question,
        ):
            selected.append(VectorEntityType.park)

        if re.search(
            r"\bschools?\b|\belementary\b|\bhigh[ -]?school\b",
            question,
        ):
            selected.append(VectorEntityType.school)

        if re.search(r"\bneighborhoods?\b", question):
            selected.append(VectorEntityType.neighborhood)

        # Explicit entity words always take precedence.
        if selected:
            return selected

        # Use semantic aliases only when no explicit entity noun exists.
        if any(
            term in question
            for term in (
                "trail",
                "library",
                "community center",
                "recreation",
                "garden",
            )
        ):
            selected.append(VectorEntityType.park)

        return selected
