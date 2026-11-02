# Day 6 — Allowlisted schema retrieval and typed query planning

## Goal

Add a safe planning layer between natural-language questions and future SQL
generation.

```text
Question
   ↓
Allowlisted schema catalog
   ↓
Relevant-schema retrieval
   ↓
Typed query plan
   ↓
No SQL and no execution in Day 6
```

## New endpoints

- `GET /api/v1/copilot/schema`
- `POST /api/v1/copilot/schema/retrieve`
- `POST /api/v1/copilot/plan`

## Example plan request

```bash
curl -sS -X POST \
  http://127.0.0.1:8000/api/v1/copilot/plan \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "Which neighborhoods contain at least three active schools and two open park features?"
  }' | python -m json.tool
```

The response contains a structured plan with `execution_allowed=false` and
`sql_generated=false`.

## Offline planner validation

```bash
python scripts/validate_day6_planner.py
```

The benchmark covers the ten Day 4 questions, one unsafe write request, and one
unsupported events question.

## Database contract verification

```bash
docker exec -i agenticdb_sj_postgis \
  psql -v ON_ERROR_STOP=1 \
  -U agenticdb \
  -d agenticdb_sj \
  < sql/verification/verify_day6.sql
```

Every `passed` value should be `t`.

## Test

```bash
python -m pytest -q
```

With Uvicorn running in another terminal:

```bash
python scripts/smoke_test_day6.py
```

## Deferred to Day 7+

- LLM provider integration
- SQL generation
- SQL AST validation
- query execution from a generated plan
- self-correction and result summarization
