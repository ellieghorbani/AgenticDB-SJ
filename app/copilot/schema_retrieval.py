"""Deterministic schema retrieval over the curated catalog."""

import re
from collections import Counter

from app.models.copilot import (
    RetrievedRelation,
    SchemaCatalogResponse,
    SchemaContextResponse,
)


_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "each", "for",
    "from", "have", "in", "is", "of", "on", "or", "that", "the", "to",
    "what", "which", "with",
}


def _normalize_token(token: str) -> str:
    token = token.lower().strip("_- ")
    irregular = {
        "schools": "school",
        "parks": "park",
        "neighborhoods": "neighborhood",
        "features": "feature",
        "distances": "distance",
        "records": "record",
    }
    if token in irregular:
        return irregular[token]
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokens(text: str) -> list[str]:
    raw = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [
        normalized
        for token in raw
        if (normalized := _normalize_token(token)) and normalized not in _STOP_WORDS
    ]


class SchemaRetriever:
    """Rank allowlisted relations using transparent token-overlap scoring."""

    def __init__(self, catalog: SchemaCatalogResponse):
        self.catalog = catalog

    def retrieve(self, question: str, top_k: int = 5) -> SchemaContextResponse:
        question_lower = question.lower()
        question_tokens = Counter(_tokens(question))
        ranked: list[RetrievedRelation] = []

        for relation in self.catalog.relations:
            if not relation.available:
                continue

            relation_terms: list[str] = []
            relation_terms.extend(_tokens(relation.qualified_name.replace(".", " ")))
            relation_terms.extend(_tokens(relation.description))
            for alias in relation.aliases:
                relation_terms.extend(_tokens(alias))
            for column in relation.columns:
                relation_terms.extend(_tokens(column.name.replace("_", " ")))
                relation_terms.extend(_tokens(column.description))
                for tag in column.semantic_tags:
                    relation_terms.extend(_tokens(tag))

            term_counts = Counter(relation_terms)
            matched_terms = sorted(set(question_tokens).intersection(term_counts))
            score = sum(
                min(question_tokens[term], 2) * min(term_counts[term], 4)
                for term in matched_terms
            )

            for alias in relation.aliases:
                if alias.lower() in question_lower:
                    score += 8

            relation_name_phrase = relation.relation_name.replace("_", " ").lower()
            if relation_name_phrase in question_lower:
                score += 6

            if relation.geometry_column and any(
                token in question_tokens
                for token in {"near", "nearest", "within", "distance", "intersect"}
            ):
                score += 2

            if score > 0:
                ranked.append(
                    RetrievedRelation(
                        relation=relation,
                        relevance_score=round(float(score), 3),
                        matched_terms=matched_terms,
                    )
                )

        ranked.sort(
            key=lambda item: (
                -item.relevance_score,
                item.relation.qualified_name,
            )
        )
        selected = ranked[:top_k]
        selected_names = {item.relation.qualified_name for item in selected}
        joins = [
            join
            for join in self.catalog.joins
            if join.left_relation in selected_names
            and join.right_relation in selected_names
        ]

        return SchemaContextResponse(
            question=question,
            relations=selected,
            joins=joins,
        )
