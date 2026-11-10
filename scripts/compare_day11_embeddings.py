#!/usr/bin/env python3
"""Compare local MiniLM and OpenAI pgvector retrieval on the Day 10 cases."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.config import get_settings
from app.copilot.embeddings import (
    OpenAIEmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
)
from app.copilot.vector_router import DeterministicVectorRouter
from app.copilot.vector_search import VectorSearchService
from app.db.connection import open_db_connection
from app.models.vector import VectorSearchRequest


BENCHMARK_PATH = Path("benchmarks/day10/vector_cases.json")
OUTPUT_PATH = Path("results/day11/embedding_comparison.json")


def build_request(decision) -> VectorSearchRequest:
    return VectorSearchRequest(
        query=decision.query_text,
        entity_types=decision.entity_types,
        top_k=decision.top_k,
        min_similarity=decision.min_similarity,
        only_open_parks=decision.only_open_parks,
        education_level_code=decision.education_level_code,
    )


def main() -> None:
    settings = get_settings()
    if not settings.openai_api_key_configured:
        raise SystemExit("OPENAI_API_KEY is required for provider comparison")

    local = SentenceTransformerEmbeddingProvider(
        settings.embedding_model_name,
        settings.embedding_dimensions,
        device=settings.embedding_device,
        batch_size=settings.embedding_batch_size,
    )
    hosted = OpenAIEmbeddingProvider(
        api_key=settings.openai_api_key_value,
        api_model=settings.openai_embedding_model,
        dimensions=settings.openai_embedding_dimensions,
        batch_size=settings.openai_embedding_batch_size,
        timeout_seconds=settings.openai_llm_timeout_seconds,
    )

    local_connection = open_db_connection(settings)
    hosted_connection = open_db_connection(settings)
    try:
        local_connection.execute("SET TRANSACTION READ ONLY")
        hosted_connection.execute("SET TRANSACTION READ ONLY")
        local_service = VectorSearchService(local_connection, settings, local)
        hosted_service = VectorSearchService(hosted_connection, settings, hosted)

        local_status = local_service.status()
        hosted_status = hosted_service.status()
        if hosted_status.embedded_document_count != 1128:
            raise SystemExit(
                "OpenAI embeddings are not loaded. Set EMBEDDING_PROVIDER=openai "
                "and run: python -m scripts.build_day11_embeddings"
            )

        router = DeterministicVectorRouter()
        cases = json.loads(BENCHMARK_PATH.read_text())["cases"][:5]
        results = []
        for case in cases:
            decision = router.route(
                case["question"],
                top_k=10,
                min_similarity=0.0,
            )
            request = build_request(decision)
            local_result = local_service.search(request)
            hosted_result = hosted_service.search(request)
            local_ids = {
                (match.entity_type.value, match.entity_id)
                for match in local_result.matches
            }
            hosted_ids = {
                (match.entity_type.value, match.entity_id)
                for match in hosted_result.matches
            }
            union = local_ids | hosted_ids
            overlap = local_ids & hosted_ids
            results.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "local_model": local.model_name,
                    "openai_model": hosted.model_name,
                    "local_elapsed_ms": local_result.elapsed_ms,
                    "openai_elapsed_ms": hosted_result.elapsed_ms,
                    "overlap_at_10": len(overlap),
                    "jaccard_at_10": round(len(overlap) / len(union), 4)
                    if union
                    else 1.0,
                    "local_top_title": local_result.matches[0].title
                    if local_result.matches
                    else None,
                    "openai_top_title": hosted_result.matches[0].title
                    if hosted_result.matches
                    else None,
                }
            )
            print(
                f"{case['id']}: overlap@10={len(overlap)} "
                f"local={local_result.elapsed_ms:.3f} ms "
                f"openai={hosted_result.elapsed_ms:.3f} ms"
            )

        report = {
            "local_status": local_status.model_dump(mode="json"),
            "openai_status": hosted_status.model_dump(mode="json"),
            "results": results,
        }
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n")
        print(f"Wrote {OUTPUT_PATH}")
    finally:
        local_connection.rollback()
        hosted_connection.rollback()
        local_connection.close()
        hosted_connection.close()


if __name__ == "__main__":
    main()
