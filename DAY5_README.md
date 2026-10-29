# Day 5 — Read-only FastAPI database service

## Goal

Expose the trusted PostgreSQL/PostGIS layer through typed HTTP endpoints before
adding a natural-language agent.

## Architecture

```text
HTTP request
    ↓
FastAPI route + Pydantic validation
    ↓
QueryService
    ↓
Parameterized SQL in a read-only transaction
    ↓
PostgreSQL/PostGIS
    ↓
Typed JSON response
```

The API does not accept raw SQL and does not use an LLM.

## Endpoints

- `GET /`
- `GET /health/live`
- `GET /health/ready`
- `GET /api/v1/snapshot`
- `GET /api/v1/neighborhoods`
- `GET /api/v1/neighborhoods/{neighborhood_id}`
- `GET /api/v1/schools/near-open-parks`
- `GET /api/v1/parks/{facility_id}/nearby-schools`

## Install

Merge the lines in `requirements-day5.txt` into the project's existing
`requirements.txt`, then install:

```bash
python -m pip install --no-cache-dir -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/health/ready`

## Test

```bash
python -m pytest -q
```

With the API running in a second terminal:

```bash
python scripts/smoke_test_day5.py
```

## Security properties in this milestone

- No endpoint accepts SQL text.
- Every user value is passed as a Psycopg parameter.
- Every request uses a read-only transaction.
- A statement timeout limits database work.
- Database errors return a generic 503 response.
- Route inputs and responses are validated with Pydantic models.

## Deferred work

A dedicated least-privilege database role, connection pooling, request logging,
query-plan inspection, and the natural-language planner are intentionally left
for later milestones.
