# AgenticDB-SJ Final Technical Report

Generated: `2026-11-10T14:50:39.888840+00:00`  
Version: `1.0.0`

## Executive summary

AgenticDB-SJ is a provenance-aware natural-language database copilot over
real public relational, geospatial, and vector data. It combines PostgreSQL,
PostGIS, pgvector, FastAPI, OpenAI structured planning, deterministic
parameterized SQL templates, independent SQLGlot AST validation, restricted
read-only execution, and row-level evidence.

The final release aggregated **102 benchmark checks**
across 8 validation suites, with an aggregate pass
rate of **100.0%**.

## Data snapshot

- Neighborhood polygons: **297**
- Park-source features: **611**
- Active school records: **10537**
- Schools in San José spatial scope: **220**
- Distinct semantic documents: **1128**
- Stored embedding vectors: **2256**
- Embedding models stored: **2**

## Evaluation

| Benchmark | Passed | Pass rate | Mean ms | P95 ms |
| --- | --- | --- | --- | --- |
| Human-reviewed SQL/PostGIS gold benchmark | 10/10 | 100.0% | 5727.995 | 15872.558 |
| Typed query planning | 12/12 | 100.0% | — | — |
| Parameterized SQL generation | 13/13 | 100.0% | — | — |
| AST safety validation | 21/21 | 100.0% | — | — |
| Restricted read-only execution | 13/13 | 100.0% | 863.736 | 4302.514 |
| Agent routing and tool-use reliability | 13/13 | 100.0% | 668.048 | 4366.258 |
| Semantic and hybrid vector retrieval | 7/7 | 100.0% | — | — |
| OpenAI structured planning | 13/13 | 100.0% | 2408.196 | 6235.935 |

## Database and retrieval stack

- PostgreSQL: `16.9 (Debian 16.9-1.pgdg110+1)`
- PostGIS: `3.5 USE_GEOS=1 USE_PROJ=1 USE_STATS=1`
- pgvector: `0.8.7`
- HNSW index present: `True`
- Restricted execution role: `agenticdb_reader`

## Hosted-model evaluation

- Model: `gpt-5.6-terra`
- LLM intent accuracy: **100.0%**
- Deterministic baseline intent accuracy: **61.5%**
- Input tokens: **13190**
- Output tokens: **1118**
- Estimated benchmark cost: **None**

## Embedding-provider comparison

- Cases: **5**
- Mean overlap@10: **2.0**
- Mean Jaccard@10: **0.117**
- Local mean latency: **3.529 ms**
- OpenAI mean latency: **5.729 ms**

## Safety architecture

1. A local safety gate blocks destructive requests before hosted-model calls.
2. Hosted planning returns a strict typed intent and slots, not executable SQL.
3. The deterministic planner reconstructs an allowlisted query plan.
4. Reviewed templates generate parameterized PostgreSQL/PostGIS SQL.
5. SQLGlot independently reparses and validates the AST.
6. Only one bounded `SELECT` statement can execute.
7. PostgreSQL executes under `agenticdb_reader` in a read-only transaction.
8. Answers are synthesized only from returned rows or vector matches.
9. Evidence rows, source relations, tool traces, and query fingerprints are retained.

## Reproducibility

Run:

```bash
python -m scripts.build_day12_release
python -m scripts.validate_day12_release
python -m pytest -q
```

Start the portfolio demo:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/demo`.

## Limitations

- Supported SQL intents are deliberately constrained to reviewed templates.
- Real-time events, traffic, and school-attendance boundaries are outside v1.0.
- Hosted-model behavior and API costs can change over time.
- Semantic suitability remains an inference unless directly supported by source text.
- The current geographic focus is San José and the supplied source boundaries.
