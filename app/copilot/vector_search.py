"""pgvector-backed semantic and metadata-filtered hybrid retrieval."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from psycopg import Connection
from psycopg import sql as psycopg_sql

from app.core.config import Settings
from app.copilot.embeddings import EmbeddingProvider
from app.models.vector import (
    VectorEntityType,
    VectorMatch,
    VectorSearchRequest,
    VectorSearchResponse,
    VectorStatusResponse,
)


_SEARCH_SQL = """
WITH candidates AS (
    SELECT
        document_id,
        entity_type,
        entity_id,
        title,
        source_text,
        metadata,
        1 - (embedding <=> %s) AS similarity
    FROM semantic.entity_documents
    WHERE embedding_model = %s
      AND entity_type = ANY(%s)
      AND (
            NOT %s
            OR entity_type <> 'park'
            OR metadata->>'current_status' = 'Open'
          )
      AND (
            %s::text IS NULL
            OR entity_type <> 'school'
            OR metadata->>'education_level_code' = %s::text
          )
    ORDER BY embedding <=> %s, document_id
    LIMIT %s
)
SELECT
    document_id,
    entity_type,
    entity_id,
    title,
    source_text,
    metadata,
    similarity
FROM candidates
WHERE similarity >= %s
ORDER BY similarity DESC, entity_type, entity_id;
"""


class VectorSearchService:
    """Encode a query and perform safe pgvector cosine search."""

    provider_name = "sentence_transformers_pgvector_day10"

    def __init__(
        self,
        connection: Connection,
        settings: Settings,
        embedder: EmbeddingProvider,
    ):
        self.connection = connection
        self.settings = settings
        self.embedder = embedder

    def status(self) -> VectorStatusResponse:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT extversion
                FROM pg_extension
                WHERE extname = 'vector'
                """
            )
            extension = cursor.fetchone()
            if extension is None:
                raise RuntimeError("pgvector extension is not installed")

            cursor.execute(
                """
                SELECT
                    COUNT(*)::integer AS document_count,
                    COUNT(embedding)::integer AS embedded_document_count
                FROM semantic.entity_documents
                WHERE embedding_model = %s
                """,
                (self.settings.embedding_model_name,),
            )
            totals = cursor.fetchone()
            assert totals is not None

            cursor.execute(
                """
                SELECT entity_type, COUNT(*)::integer AS count
                FROM semantic.entity_documents
                WHERE embedding_model = %s
                GROUP BY entity_type
                ORDER BY entity_type
                """,
                (self.settings.embedding_model_name,),
            )
            entity_counts = {
                str(row["entity_type"]): int(row["count"])
                for row in cursor.fetchall()
            }

            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_indexes
                    WHERE schemaname = 'semantic'
                      AND indexname = 'idx_entity_documents_embedding_hnsw'
                ) AS present
                """
            )
            index_row = cursor.fetchone()
            assert index_row is not None

        return VectorStatusResponse(
            status="ready",
            extension_version=str(extension["extversion"]),
            document_count=int(totals["document_count"]),
            embedded_document_count=int(totals["embedded_document_count"]),
            embedding_model=self.settings.embedding_model_name,
            embedding_dimensions=self.settings.embedding_dimensions,
            entity_counts=entity_counts,
            hnsw_index_present=bool(index_row["present"]),
        )

    def search(self, request: VectorSearchRequest) -> VectorSearchResponse:
        from pgvector.psycopg import register_vector

        register_vector(self.connection)
        query_vector = self.embedder.encode_query(request.query)
        entity_types = [entity.value for entity in request.entity_types]

        with self.connection.cursor() as cursor:
            cursor.execute(
                psycopg_sql.SQL("SET LOCAL ROLE {}").format(
                    psycopg_sql.Identifier(self.settings.copilot_execution_role)
                )
            )
            cursor.execute(
                "SELECT set_config('statement_timeout', %s, true)",
                (str(self.settings.vector_search_timeout_ms),),
            )
            cursor.execute(
                "SELECT set_config('hnsw.ef_search', %s, true)",
                (str(self.settings.vector_hnsw_ef_search),),
            )
            cursor.execute(
                """
                SELECT
                    current_setting('transaction_read_only') = 'on'
                        AS transaction_read_only,
                    current_user AS database_role
                """
            )
            state = cursor.fetchone()
            assert state is not None
            if not bool(state["transaction_read_only"]):
                raise RuntimeError("vector search requires a read-only transaction")
            if str(state["database_role"]) != self.settings.copilot_execution_role:
                raise RuntimeError("vector search did not assume the restricted role")

            started = perf_counter()
            cursor.execute(
                _SEARCH_SQL,
                (
                    query_vector,
                    self.settings.embedding_model_name,
                    entity_types,
                    request.only_open_parks,
                    request.education_level_code,
                    request.education_level_code,
                    query_vector,
                    request.top_k,
                    request.min_similarity,
                ),
            )
            rows = [dict(row) for row in cursor.fetchall()]
            elapsed_ms = round((perf_counter() - started) * 1000.0, 3)

        matches = [
            VectorMatch(
                document_id=int(row["document_id"]),
                entity_type=VectorEntityType(str(row["entity_type"])),
                entity_id=str(row["entity_id"]),
                title=str(row["title"]),
                source_text=str(row["source_text"]),
                similarity=round(float(row["similarity"]), 6),
                metadata=dict(row["metadata"] or {}),
            )
            for row in rows
        ]
        return VectorSearchResponse(
            model=self.settings.embedding_model_name,
            dimensions=self.settings.embedding_dimensions,
            query=request.query,
            entity_types=list(request.entity_types),
            only_open_parks=request.only_open_parks,
            education_level_code=request.education_level_code,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
            match_count=len(matches),
            matches=matches,
            elapsed_ms=elapsed_ms,
            database_role=str(state["database_role"]),
            transaction_read_only=bool(state["transaction_read_only"]),
        )
