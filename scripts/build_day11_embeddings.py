#!/usr/bin/env python3
"""Build embeddings with the configured local or OpenAI provider."""

from __future__ import annotations

import json

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from app.core.config import get_settings
from app.copilot.embeddings import cached_configured_embedding_provider
from scripts.build_day10_embeddings import fetch_documents


def main() -> None:
    settings = get_settings()
    if settings.active_embedding_dimensions != 384:
        raise RuntimeError(
            "The current semantic.entity_documents schema uses vector(384). "
            "Set the active provider dimensions to 384 before rebuilding."
        )
    api_key = settings.openai_api_key_value
    provider = cached_configured_embedding_provider(
        settings.embedding_provider,
        settings.embedding_model_name,
        settings.embedding_dimensions,
        settings.embedding_device,
        settings.embedding_batch_size,
        api_key,
        settings.openai_embedding_model,
        settings.openai_embedding_dimensions,
        settings.openai_embedding_batch_size,
        settings.openai_llm_timeout_seconds,
    )

    connection = psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password.get_secret_value(),
        connect_timeout=settings.database_connect_timeout_seconds,
        application_name="agenticdb_sj_day11_embeddings",
        row_factory=dict_row,
        autocommit=True,
    )
    register_vector(connection)

    run_id: int | None = None
    try:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO semantic.embedding_runs (
                        embedding_model,
                        embedding_dimensions,
                        status
                    )
                    VALUES (%s, %s, 'running')
                    RETURNING embedding_run_id
                    """,
                    (provider.model_name, provider.dimensions),
                )
                row = cursor.fetchone()
                assert row is not None
                run_id = int(row["embedding_run_id"])

        documents = fetch_documents(connection)
        expected_counts = {"park": 611, "school": 220, "neighborhood": 297}
        actual_counts = {
            entity_type: sum(
                document.entity_type == entity_type for document in documents
            )
            for entity_type in expected_counts
        }
        if actual_counts != expected_counts:
            raise RuntimeError(
                f"source snapshot mismatch: expected {expected_counts}, "
                f"received {actual_counts}"
            )

        print(
            f"Encoding {len(documents)} real source-derived documents with "
            f"{provider.model_name}..."
        )
        vectors = provider.encode_documents(
            [document.source_text for document in documents]
        )

        rows = [
            (
                document.entity_type,
                document.entity_id,
                document.title,
                document.source_text,
                document.source_text_hash,
                json.dumps(document.metadata, sort_keys=True),
                provider.model_name,
                provider.dimensions,
                vectors[index],
                document.source_id,
            )
            for index, document in enumerate(documents)
        ]

        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM semantic.entity_documents "
                    "WHERE embedding_model = %s",
                    (provider.model_name,),
                )
                cursor.executemany(
                    """
                    INSERT INTO semantic.entity_documents (
                        entity_type,
                        entity_id,
                        title,
                        source_text,
                        source_text_hash,
                        metadata,
                        embedding_model,
                        embedding_dimensions,
                        embedding,
                        source_id
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s
                    )
                    ON CONFLICT (entity_type, entity_id, embedding_model)
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        source_text = EXCLUDED.source_text,
                        source_text_hash = EXCLUDED.source_text_hash,
                        metadata = EXCLUDED.metadata,
                        embedding_dimensions = EXCLUDED.embedding_dimensions,
                        embedding = EXCLUDED.embedding,
                        source_id = EXCLUDED.source_id,
                        updated_at = now()
                    """,
                    rows,
                )
                cursor.execute(
                    """
                    UPDATE semantic.embedding_runs
                    SET completed_at = now(),
                        source_document_count = %s,
                        embedded_document_count = %s,
                        status = 'succeeded'
                    WHERE embedding_run_id = %s
                    """,
                    (len(documents), len(rows), run_id),
                )

        print("Day 11 embeddings loaded successfully")
        print(f"  provider: {provider.provider_name}")
        print(f"  model key: {provider.model_name}")
        print(f"  parks: {actual_counts['park']}")
        print(f"  schools: {actual_counts['school']}")
        print(f"  neighborhoods: {actual_counts['neighborhood']}")
        print(f"  total: {len(documents)}")
    except Exception as exc:
        if run_id is not None:
            try:
                with connection.transaction():
                    connection.execute(
                        """
                        UPDATE semantic.embedding_runs
                        SET completed_at = now(),
                            status = 'failed',
                            error_message = %s
                        WHERE embedding_run_id = %s
                        """,
                        (str(exc), run_id),
                    )
            except Exception:
                pass
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
