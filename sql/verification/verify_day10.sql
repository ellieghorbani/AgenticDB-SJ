\set ON_ERROR_STOP on
\pset pager off

WITH checks AS (
    SELECT
        'vector_extension_exists' AS metric,
        EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') AS passed
    UNION ALL
    SELECT
        'semantic_table_exists',
        to_regclass('semantic.entity_documents') IS NOT NULL
    UNION ALL
    SELECT
        'document_count_1128',
        (SELECT COUNT(*) FROM semantic.entity_documents) = 1128
    UNION ALL
    SELECT
        'park_document_count_611',
        (SELECT COUNT(*) FROM semantic.entity_documents WHERE entity_type = 'park') = 611
    UNION ALL
    SELECT
        'school_document_count_220',
        (SELECT COUNT(*) FROM semantic.entity_documents WHERE entity_type = 'school') = 220
    UNION ALL
    SELECT
        'neighborhood_document_count_297',
        (SELECT COUNT(*) FROM semantic.entity_documents WHERE entity_type = 'neighborhood') = 297
    UNION ALL
    SELECT
        'all_embeddings_384_dimensions',
        NOT EXISTS (
            SELECT 1
            FROM semantic.entity_documents
            WHERE vector_dims(embedding) <> 384
        )
    UNION ALL
    SELECT
        'hnsw_index_exists',
        EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE schemaname = 'semantic'
              AND indexname = 'idx_entity_documents_embedding_hnsw'
        )
    UNION ALL
    SELECT
        'reader_select_allowed',
        has_table_privilege(
            'agenticdb_reader',
            'semantic.entity_documents',
            'SELECT'
        )
    UNION ALL
    SELECT
        'reader_insert_denied',
        NOT has_table_privilege(
            'agenticdb_reader',
            'semantic.entity_documents',
            'INSERT'
        )
)
SELECT metric, passed
FROM checks
ORDER BY metric;

SELECT
    entity_type,
    COUNT(*) AS document_count,
    MIN(vector_dims(embedding)) AS min_dimensions,
    MAX(vector_dims(embedding)) AS max_dimensions
FROM semantic.entity_documents
GROUP BY entity_type
ORDER BY entity_type;

SELECT
    embedding_run_id,
    embedding_model,
    embedding_dimensions,
    source_document_count,
    embedded_document_count,
    status,
    started_at,
    completed_at
FROM semantic.embedding_runs
ORDER BY embedding_run_id DESC
LIMIT 5;
