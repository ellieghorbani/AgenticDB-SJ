CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS metadata;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE IF NOT EXISTS metadata.source_registry (
    source_id BIGSERIAL PRIMARY KEY,
    source_key TEXT NOT NULL UNIQUE,
    publisher TEXT NOT NULL,
    dataset_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    local_file TEXT NOT NULL,
    file_format TEXT NOT NULL,
    retrieved_at DATE NOT NULL,
    file_sha256 CHAR(64) NOT NULL,
    row_count INTEGER,
    usage_terms TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS metadata.ingestion_runs (
    ingestion_run_id BIGSERIAL PRIMARY KEY,
    source_id BIGINT NOT NULL REFERENCES metadata.source_registry(source_id),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    rows_read INTEGER,
    rows_loaded INTEGER,
    rows_rejected INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK (status IN ('started', 'succeeded', 'failed')),
    error_message TEXT,
    code_version TEXT
);
