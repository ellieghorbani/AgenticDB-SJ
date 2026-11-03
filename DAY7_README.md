# AgenticDB-SJ Day 7

## Milestone

Generate parameterized PostgreSQL/PostGIS SQL from validated Day 6 plans without executing the SQL.

## Files added

```text
app/copilot/sql_generator.py
app/models/sql_generation.py
app/api/routes/sql_generation.py
benchmarks/day7/sql_generation_cases.json
scripts/validate_day7_sql.py
scripts/smoke_test_day7.py
tests/copilot/test_sql_generator.py
tests/api/test_sql_generation_routes.py
docs/day7_sql_generation.md
```

The package also updates API wiring and the application version to `0.7.0`.

## Validate offline

```bash
python -m pytest -q
python scripts/validate_day7_sql.py
```

Expected benchmark result:

```text
SQL generation benchmark: 13/13 passed (100.0%)
```

## Run the API

Terminal 1:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2:

```bash
curl -sS -X POST \
  http://127.0.0.1:8000/api/v1/copilot/sql \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "Which neighborhoods contain at least three active schools and two open park features?"
  }' \
  | python -m json.tool
```

The response should contain parameterized SQL and:

```json
{
  "status": "generated",
  "execution_allowed": false,
  "sql_generated": true
}
```

## Smoke test

Keep Uvicorn running, then execute:

```bash
python scripts/smoke_test_day7.py
```

Expected:

```text
Day 7 SQL-generation smoke test PASSED
```

## Safety boundary

Day 7 does not execute generated SQL. Unsafe, unsupported, or unresolved questions return `sql: null`.
