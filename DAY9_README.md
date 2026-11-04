# AgenticDB-SJ — Day 9

## Agent routing, traced tools, and evidence-backed answers

Day 9 combines the trusted Day 6–8 components into a single auditable agent
workflow. No external LLM is required yet; the workflow is deterministic so its
tool behavior can be measured before adding a model provider.

## 1. Update `main` and create the branch

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/day-9-agent-orchestration
git push -u origin feature/day-9-agent-orchestration
```

## 2. No new Python dependency

Day 9 uses the dependencies already installed through Day 8.

Optional `.env` setting:

```env
AGENT_DEFAULT_EVIDENCE_ROWS=5
```

## 3. Run tests

```bash
python -m pytest -q
```

## 4. Run the live workflow benchmark

Make sure PostgreSQL/PostGIS is healthy and the Day 8 restricted role exists:

```bash
docker compose ps
python scripts/validate_day9_agent.py
```

Expected final result:

```text
Agent workflow benchmark: 13/13 passed (100.0%)
```

The report is written to:

```text
results/day9/agent_validation.json
```

## 5. Start the API

```bash
python -m uvicorn \
  app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
```

### List tools

```bash
curl -sS \
  http://127.0.0.1:8000/api/v1/copilot/agent/tools \
  | python -m json.tool
```

### Run the agent

```bash
curl -sS -X POST \
  http://127.0.0.1:8000/api/v1/copilot/agent/run \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "Which neighborhoods contain at least three active schools and two open park features?",
    "evidence_limit": 3
  }' \
  | python -m json.tool
```

Important expected values:

```text
status: completed
route: relational_sql
answer.row_count: 15
execution.database_role: agenticdb_reader
execution.transaction_read_only: true
tool_trace: 6 entries
```

### Unsafe request

```bash
curl -sS -X POST \
  http://127.0.0.1:8000/api/v1/copilot/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"question": "Delete all schools and drop the parks table"}' \
  | python -m json.tool
```

Expected:

```text
status: blocked
route: blocked
execution: null
sql.generate: skipped
sql.validate: skipped
sql.execute: skipped
```

## 6. Run the live HTTP smoke test

Keep Uvicorn running:

```bash
python scripts/smoke_test_day9.py
```

Expected:

```text
Day 9 agent orchestration smoke test PASSED
```

## Completion criteria

- Six tools are exposed through the tool catalog.
- Supported questions use all six tools in order.
- Unsafe, unsupported, and ambiguous questions skip SQL execution.
- Executed runs use `agenticdb_reader` and a read-only transaction.
- Answers include bounded supporting rows and source relations.
- Tool traces include status and latency.
- The 13-case live benchmark passes.
- Pytest and the HTTP smoke test pass.
