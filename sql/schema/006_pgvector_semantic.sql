\set ON_ERROR_STOP on

CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS semantic;

CREATE TABLE IF NOT EXISTS semantic.embedding_runs (
    embedding_run_id BIGSERIAL PRIMARY KEY,
    embedding_model TEXT NOT NULL,
    embedding_dimensions INTEGER NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    source_document_count INTEGER,
    embedded_document_count INTEGER,
    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS semantic.entity_documents (
    document_id BIGSERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL
        CHECK (entity_type IN ('park', 'school', 'neighborhood')),
    entity_id TEXT NOT NULL,
    title TEXT NOT NULL,
    source_text TEXT NOT NULL,
    source_text_hash CHAR(64) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding_model TEXT NOT NULL,
    embedding_dimensions INTEGER NOT NULL CHECK (embedding_dimensions = 384),
    embedding vector(384) NOT NULL,
    source_id BIGINT REFERENCES metadata.source_registry(source_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (entity_type, entity_id, embedding_model)
);

CREATE INDEX IF NOT EXISTS idx_entity_documents_type_model
ON semantic.entity_documents (entity_type, embedding_model);

CREATE INDEX IF NOT EXISTS idx_entity_documents_metadata
ON semantic.entity_documents USING GIN (metadata);

CREATE INDEX IF NOT EXISTS idx_entity_documents_embedding_hnsw
ON semantic.entity_documents
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

GRANT USAGE ON SCHEMA semantic TO agenticdb_reader;
REVOKE ALL ON ALL TABLES IN SCHEMA semantic FROM agenticdb_reader;
GRANT SELECT ON semantic.entity_documents TO agenticdb_reader;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE
ON semantic.entity_documents FROM agenticdb_reader;
