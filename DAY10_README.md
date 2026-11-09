# Day 10 — pgvector Semantic and Hybrid Retrieval

Day 10 adds local embeddings, pgvector storage, HNSW cosine search, structured
metadata filters, deterministic semantic routing, evidence-backed vector
answers, tests, and a live benchmark.

## 1. Build PostgreSQL with PostGIS and pgvector

The updated `compose.yaml` builds a PostgreSQL 16 image containing both PostGIS
3.5 and pgvector 0.8.7.

```bash
docker compose down
docker compose up -d --build
```

Do **not** add `-v`; the existing named PostgreSQL volume must be preserved.

Verify the container:

```bash
docker compose ps
```

## 2. Install Python dependencies

```bash
while IFS= read -r requirement; do
    [ -z "$requirement" ] && continue
    grep -qxF "$requirement" requirements.txt \
        || echo "$requirement" >> requirements.txt
done < requirements-day10.txt
rm requirements-day10.txt
python -m pip install --no-cache-dir -r requirements.txt
python -m pip check
```

## 3. Create the semantic database schema

```bash
docker exec -i agenticdb_sj_postgis \
  psql -v ON_ERROR_STOP=1 \
  -U agenticdb \
  -d agenticdb_sj \
  < sql/schema/006_pgvector_semantic.sql
```

## 4. Build the embeddings

```bash
python scripts/build_day10_embeddings.py
```

The first run downloads the local embedding model. Expected counts:

```text
parks:         611
schools:       220
neighborhoods: 297
total:         1128
```

## 5. Verify the database

```bash
docker exec -i agenticdb_sj_postgis \
  psql -v ON_ERROR_STOP=1 \
  -U agenticdb \
  -d agenticdb_sj \
  < sql/verification/verify_day10.sql
```

Every `passed` value should be `t`.

## 6. Run tests and benchmark

```bash
python -m pytest -q
python scripts/validate_day10_vector.py
```

Expected benchmark result:

```text
Vector benchmark: 7/7 passed (100.0%)
```

## 7. Run the API smoke test

Terminal 1:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2:

```bash
python scripts/smoke_test_day10.py
```

Expected final line:

```text
Day 10 pgvector semantic/hybrid smoke test PASSED
```

## 8. Example routed vector question

```bash
curl -sS -X POST \
  http://127.0.0.1:8000/api/v1/copilot/vector/run \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "Find open park features related to community centers and libraries.",
    "top_k": 5,
    "evidence_limit": 3,
    "min_similarity": 0.15
  }' \
  | python -m json.tool
```

The expected route is `hybrid_vector`: cosine similarity plus the structured
`current_status = Open` metadata filter.
