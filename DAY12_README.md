# Day 12 — Final evaluation and v1.0 portfolio release

Day 12 turns the completed engineering milestones into a measurable,
demonstrable, and CV-ready release.

## What is added

- Interactive, dependency-free `/demo` page
- `/api/v1/release/metrics` and `/manifest` endpoints
- Final evaluation aggregation across Days 4 and 6–11
- Live database, PostGIS, pgvector, HNSW, and embedding-model snapshot
- Generated final technical report
- Generated CV bullets using measured values
- Architecture diagrams
- Release manifest with SHA-256 checksums
- Security, contribution, changelog, and citation files
- Final release validation and smoke test
- Application version `1.0.0`

## Required inputs

Before building the release, run and retain successful reports from:

```text
results/gold/day4/manifest.json
results/day6/planner_validation.json
results/day7/sql_generation_validation.json
results/day8/ast_validation.json
results/day8/execution_validation.json
results/day9/agent_validation.json
results/day10/vector_validation.json
results/day11/llm_validation.json
```

The embedding comparison is optional:

```text
results/day11/embedding_comparison.json
```

## Build

```bash
python -m scripts.build_day12_release
```

This reads the committed benchmark reports and a live read-only database
snapshot. It does not rerun paid OpenAI benchmarks.

## Validate

```bash
python -m scripts.validate_day12_release
python -m pytest -q
```

## Demo

Start Uvicorn:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open:

```text
http://127.0.0.1:8000/demo
```

From another terminal:

```bash
python -m scripts.smoke_test_day12
```

The smoke test uses the deterministic provider and does not make a paid OpenAI
planning call.

## Git workflow

Create and use:

```text
feature/day-12-v1-release
```

Commit the implementation, generated metrics/report/CV artifacts, and release
documentation. Open a pull request into `main`, review it, and squash merge.

After merge:

```bash
git switch main
git pull --ff-only origin main
git tag -a v1.0.0 -m "AgenticDB-SJ v1.0.0 portfolio release"
git push origin v1.0.0
```
