# CV-Ready AgenticDB-SJ Bullets

Use only after the generated metrics have been reviewed.

## Detailed version

- Built AgenticDB-SJ, a provenance-aware natural-language database copilot over
  **11,445 real public records**, using PostgreSQL, PostGIS, pgvector,
  FastAPI, Python, and OpenAI structured planning for relational, spatial,
  semantic, and hybrid retrieval.
- Implemented allowlisted schema retrieval, deterministic parameterized SQL,
  SQLGlot AST validation, bounded result policies, and restricted read-only
  PostgreSQL execution with query fingerprints and row-level evidence.
- Indexed **1,128 distinct source-derived
  documents** as **2,256 stored vectors** with
  384-dimensional embeddings and HNSW cosine search, supporting local MiniLM
  and hosted OpenAI embedding providers through configuration.
- Evaluated planning, SQL generation, adversarial safety, execution, agent
  routing, vector retrieval, and hosted-model planning across
  **102 benchmark checks**, achieving an aggregate
  pass rate of **100.0%**.
- Compared hosted and deterministic planning on the same benchmark;
  hosted-model intent accuracy was **100.0%**
  and the deterministic baseline was
  **61.5%**.

## Two-bullet resume version

- Built a natural-language database copilot over **11,445 real public
  records** using PostgreSQL, PostGIS, pgvector, FastAPI, and OpenAI structured
  planning, supporting relational, spatial, semantic, and hybrid retrieval.
- Implemented parameterized SQL generation, independent AST guardrails,
  restricted read-only execution, HNSW vector search, evidence-backed answers,
  and an evaluation suite with **102 benchmark checks**
  at **100.0%** aggregate pass rate.

## One-line version

Developed a provenance-aware database copilot using PostgreSQL/PostGIS,
pgvector, FastAPI, and OpenAI structured planning, with safe SQL execution,
hybrid retrieval, and benchmarked tool-use reliability.
