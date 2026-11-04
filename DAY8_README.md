# AgenticDB-SJ — Day 8

## Independent AST validation and controlled read-only execution

Day 8 converts the Day 7 SQL artifact into an executable database operation only
after an independent SQLGlot AST policy grants permission.

## 1. Install the Day 8 dependency

Merge the temporary dependency file into `requirements.txt`:

```bash
while IFS= read -r requirement; do
    [ -z "$requirement" ] && continue
    grep -qxF "$requirement" requirements.txt \
        || echo "$requirement" >> requirements.txt
done < requirements-day8.txt

rm requirements-day8.txt
python -m pip install --no-cache-dir -r requirements.txt
python -m pip check
```

The package pins SQLGlot so the AST behavior is reproducible.

## 2. Apply the restricted role and execution index

```bash
docker exec -i agenticdb_sj_postgis \
  psql -v ON_ERROR_STOP=1 \
  -U agenticdb \
  -d agenticdb_sj \
  < sql/security/001_copilot_readonly_role.sql
```

```bash
docker exec -i agenticdb_sj_postgis \
  psql -v ON_ERROR_STOP=1 \
  -U agenticdb \
  -d agenticdb_sj \
  < sql/schema/005_copilot_execution_indexes.sql
```

Verify the database security boundary:

```bash
docker exec -i agenticdb_sj_postgis \
  psql -v ON_ERROR_STOP=1 \
  -U agenticdb \
  -d agenticdb_sj \
  < sql/verification/verify_day8.sql
```

Every `passed` value should be `t`.

## 3. Optional `.env` settings

The defaults are already defined in the application. You may add:

```env
COPILOT_EXECUTION_ROLE=agenticdb_reader
COPILOT_EXECUTION_TIMEOUT_MS=15000
COPILOT_LOCK_TIMEOUT_MS=2000
COPILOT_MAX_RESULT_ROWS=1000
```

Never commit `.env`.

## 4. Run unit tests

```bash
python -m pytest -q
```

## 5. Run the offline AST benchmark

```bash
python scripts/validate_day8_ast.py
```

This writes:

```text
results/day8/ast_validation.json
```

## 6. Run the live execution benchmark

Make sure PostgreSQL/PostGIS is healthy, then run:

```bash
python scripts/validate_day8_execution.py
```

This writes:

```text
results/day8/execution_validation.json
```

The expected trusted row counts are:

```text
297, 297, 131, 220, 6, 15, 0, 134, 20, 18
```

## 7. Start the API

```bash
python -m uvicorn \
  app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
```

### Validate

```bash
curl -sS -X POST \
  http://127.0.0.1:8000/api/v1/copilot/validate \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "Which neighborhoods contain at least three active schools and two open park features?"
  }' \
  | python -m json.tool
```

### Execute

```bash
curl -sS -X POST \
  http://127.0.0.1:8000/api/v1/copilot/execute \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "Which neighborhoods contain at least three active schools and two open park features?"
  }' \
  | python -m json.tool
```

Important expected fields:

```text
status: executed
row_count: 15
database_role: agenticdb_reader
transaction_read_only: true
validation.execution_allowed: true
```

### Unsafe request

```bash
curl -sS -X POST \
  http://127.0.0.1:8000/api/v1/copilot/execute \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "Delete all schools and drop the parks table"
  }' \
  | python -m json.tool
```

Expected:

```text
status: blocked
row_count: 0
execution_allowed: false
```

## 8. Run the live smoke test

Keep Uvicorn running:

```bash
python scripts/smoke_test_day8.py
```

## Completion criteria

- SQLGlot parses all ten supported generated queries.
- All independent AST checks pass for supported queries.
- All adversarial SQL artifacts are blocked.
- Unsafe, unsupported, and unresolved questions never contact the database.
- Ten trusted queries execute with their expected row counts.
- Execution uses `agenticdb_reader`.
- PostgreSQL reports a read-only transaction.
- Unit tests, offline benchmark, live benchmark, and smoke test pass.
