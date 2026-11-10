# AgenticDB-SJ

**A provenance-aware natural-language database copilot over real relational,
geospatial, and vector data.**

AgenticDB-SJ combines PostgreSQL, PostGIS, pgvector, FastAPI, OpenAI structured
planning, deterministic parameterized SQL, SQLGlot AST validation, restricted
read-only execution, HNSW vector retrieval, and evidence-backed answers.

## Highlights

- Real public data: California schools, San José parks, and neighborhoods
- Relational SQL, PostGIS spatial search, pgvector semantic search, and hybrid retrieval
- Configurable deterministic or OpenAI structured planning
- Configurable local MiniLM or OpenAI embedding providers
- Schema-aware typed planning and reviewed SQL templates
- Independent AST validation and adversarial safety tests
- Restricted `agenticdb_reader` role and read-only transactions
- Row-level evidence, source relations, tool traces, and query fingerprints
- Reproducible benchmark artifacts and a generated final technical report

<!-- DAY12_METRICS_START -->
## Measured v1.0 results

| Evaluation suite | Passed | Pass rate |
| --- | ---: | ---: |
| Human-reviewed SQL/PostGIS gold benchmark | 10/10 | 100.0% |
| Typed query planning | 12/12 | 100.0% |
| Parameterized SQL generation | 13/13 | 100.0% |
| AST safety validation | 21/21 | 100.0% |
| Restricted read-only execution | 13/13 | 100.0% |
| Agent routing and tool-use reliability | 13/13 | 100.0% |
| Semantic and hybrid vector retrieval | 7/7 | 100.0% |
| OpenAI structured planning | 13/13 | 100.0% |

**Aggregate:** 102/102
benchmark checks passed (100.0%).

The complete generated report is in
[`docs/FINAL_REPORT.md`](docs/FINAL_REPORT.md).
<!-- DAY12_METRICS_END -->

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

```text
Question
  → safety gate
  → OpenAI/deterministic typed plan
  → allowlisted SQL or vector route
  → AST validation / pgvector retrieval
  → restricted read-only execution
  → evidence-backed answer
```

## Data snapshot

The database contains:

- 297 neighborhood polygons
- 611 park-source features
- 10,537 active California public-school records
- 220 schools in the San José spatial scope
- 1,128 source-derived semantic documents per active embedding model

No synthetic domain records are used.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --no-cache-dir -r requirements.txt
cp .env.example .env
docker compose up -d
```

Apply the schema and security migrations described in the milestone READMEs,
then load the real data and embeddings.

Start the API:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open:

- Demo: `http://127.0.0.1:8000/demo`
- API documentation: `http://127.0.0.1:8000/docs`
- Release metrics: `http://127.0.0.1:8000/api/v1/release/metrics`

## Main API workflows

```text
POST /api/v1/copilot/llm/run
POST /api/v1/copilot/agent/run
POST /api/v1/copilot/vector/run
POST /api/v1/copilot/validate
POST /api/v1/copilot/execute
```

## Final release

Generate the measured portfolio artifacts:

```bash
python -m scripts.build_day12_release
python -m scripts.validate_day12_release
python -m pytest -q
```

Run the final live smoke test while Uvicorn is active:

```bash
python -m scripts.smoke_test_day12
```

The generated artifacts include:

```text
results/day12/final_evaluation.json
results/day12/benchmark_summary.csv
results/day12/release_manifest.json
docs/FINAL_REPORT.md
docs/CV_BULLETS.md
```

## Repository structure

```text
app/            FastAPI, agent workflows, safety, SQL, and vector retrieval
benchmarks/     Reviewed evaluation cases
data/           Source manifests, raw snapshots, and processed derivatives
docs/           Architecture, reports, data dictionaries, and milestone notes
ingestion/      Audit, preparation, and PostgreSQL loading pipelines
results/        Gold outputs and benchmark reports
scripts/        Build, validation, benchmark, and smoke-test commands
sql/            Schema, indexes, views, security, verification, and gold SQL
tests/          Data contracts, unit tests, API tests, and safety tests
```

## Important limitations

- v1.0 supports a reviewed set of SQL intents rather than arbitrary SQL.
- Real-time events, traffic, and attendance boundaries are outside the current scope.
- Hosted-model behavior, pricing, and latency can change.
- Semantic suitability is an inference unless directly supported by source text.
- The geographic application scope is San José and the supplied source boundaries.

## Security

See [SECURITY.md](SECURITY.md). Never commit `.env`, API keys, passwords,
database volumes, or downloaded private files.
