# Day 11 — OpenAI-Assisted Planning and Configurable Embeddings

Day 11 adds a real hosted-model provider without weakening the deterministic
safety architecture built during Days 6–10.

## Architecture

```text
Natural-language question
        |
        v
Local unsafe-action gate
        |
        v
OpenAI Responses API structured intent + slot proposal
        |
        v
Deterministic allowlisted typed-plan reconstruction
        |
        v
Reviewed SQL template generation
        |
        v
Independent SQLGlot AST validation
        |
        v
Restricted read-only PostgreSQL execution
        |
        v
Evidence-backed deterministic answer
```

The model never authorizes execution, never receives a raw SQL execution tool,
and never bypasses the Day 7–9 safeguards.

## New endpoints

```text
GET  /api/v1/copilot/llm/status
POST /api/v1/copilot/llm/plan
POST /api/v1/copilot/llm/run
```

## Configuration

Add the following only to the ignored `.env` file:

```env
PLANNING_PROVIDER=openai
OPENAI_API_KEY=replace_with_your_api_key
OPENAI_LLM_MODEL=gpt-5.6-terra
OPENAI_LLM_TIMEOUT_SECONDS=45
OPENAI_LLM_MAX_OUTPUT_TOKENS=1200
OPENAI_FALLBACK_TO_DETERMINISTIC=true
```

The default embedding provider remains the reproducible local MiniLM baseline:

```env
EMBEDDING_PROVIDER=local
```

To build a second hosted embedding index in the same pgvector table:

```env
EMBEDDING_PROVIDER=openai
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=384
```

Then run:

```bash
python -m scripts.build_day11_embeddings
```

The hosted and local vectors coexist because they use distinct `embedding_model`
keys.

## Validation

Offline/unit validation:

```bash
python -m pytest -q
```

Live hosted-model benchmark:

```bash
python -m scripts.validate_day11_llm
```

Live HTTP smoke test while Uvicorn is running:

```bash
python -m scripts.smoke_test_day11
```

Optional embedding-provider comparison, after both indexes are loaded:

```bash
python -m scripts.compare_day11_embeddings
```

## Safety boundary

- Destructive requests are blocked before an API call.
- OpenAI returns a strict Pydantic planning proposal, not SQL.
- The proposal is translated back into the existing deterministic `QueryPlan`.
- SQL is generated only by reviewed Day 7 templates.
- SQL is reparsed by the independent Day 8 AST policy.
- Execution uses `agenticdb_reader` in a read-only transaction.
- Hosted-model failure can fall back to the deterministic planner.
- Raw SQL and raw embedding vectors remain forbidden in API requests.
- The API key stays only in `.env` and is never returned by an endpoint.

## Expected deliverables

```text
results/day11/llm_validation.json
results/day11/embedding_comparison.json   # optional
```
