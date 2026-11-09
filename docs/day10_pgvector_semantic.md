# Day 10 — pgvector Semantic and Hybrid Retrieval

## Objective

Day 10 adds vector retrieval over text derived only from the real parks, schools,
and neighborhoods already loaded into PostgreSQL/PostGIS.

No synthetic park, school, neighborhood, rating, review, or event records are
created. The only derived artifacts are deterministic source text and local
embeddings.

## Architecture

```text
Natural-language semantic question
        |
        v
Deterministic vector router
        |
        +-- semantic_vector
        +-- hybrid_vector (semantic similarity + metadata filters)
        +-- blocked / unsupported
        |
        v
Local Sentence Transformer query embedding
        |
        v
pgvector HNSW cosine search
        |
        v
Restricted agenticdb_reader role
        |
        v
Evidence-backed response
```

## Embedded entities

The embedding build creates a fixed snapshot of 1,128 documents:

- 611 park-source features
- 220 active schools inside the San José neighborhood scope
- 297 official neighborhood polygons

The source text is assembled deterministically from existing real fields. For
example, park documents use the official name, address, type/class/subclass
codes, status, planning area, owner, alias, and acreage when available.

## Model

The default local embedding model is:

```text
sentence-transformers/all-MiniLM-L6-v2
```

It produces 384-dimensional vectors. The first embedding build downloads the
model and caches it locally. No hosted embedding API or API key is required.

## Database design

`semantic.entity_documents` stores:

- entity type and source identifier
- title and source-derived text
- SHA-256 source-text hash
- structured JSON metadata
- embedding model and dimensions
- `vector(384)` embedding
- source-registry lineage

An HNSW index uses `vector_cosine_ops` for approximate cosine-distance search.
Structured filters are applied in the same PostgreSQL query.

## Routes

- `semantic_vector`: similarity search with entity-type filtering
- `hybrid_vector`: similarity search plus metadata filters such as open parks or
  school education level
- `blocked`: destructive request
- `unsupported`: no supported entity or semantic cue

## API endpoints

```text
GET  /api/v1/copilot/vector/status
POST /api/v1/copilot/vector/route
POST /api/v1/copilot/vector/search
POST /api/v1/copilot/vector/run
```

Raw embeddings are not accepted by the routed `/run` endpoint. The server
creates query embeddings using the configured local model.

## Safety boundary

- Search runs in a read-only transaction.
- Search assumes the restricted `agenticdb_reader` role.
- The reader role has SELECT only on `semantic.entity_documents`.
- The API validates entity types, result count, similarity threshold, and
  supported metadata filters.
- Destructive and unsupported requests never reach the vector database.
- Evidence is bounded by the caller's `evidence_limit`.
