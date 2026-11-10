#!/usr/bin/env python3
"""Aggregate validated project results into v1.0 release artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import __version__
from app.core.config import get_settings
from app.db.connection import open_db_connection


OUTPUT_DIR = PROJECT_ROOT / "results/day12"
METRICS_PATH = OUTPUT_DIR / "final_evaluation.json"
CSV_PATH = OUTPUT_DIR / "benchmark_summary.csv"
MANIFEST_PATH = OUTPUT_DIR / "release_manifest.json"
FINAL_REPORT_PATH = PROJECT_ROOT / "docs/FINAL_REPORT.md"
CV_BULLETS_PATH = PROJECT_ROOT / "docs/CV_BULLETS.md"
README_PATH = PROJECT_ROOT / "README.md"

BENCHMARK_SPECS = [
    {
        "key": "day4_gold",
        "label": "Human-reviewed SQL/PostGIS gold benchmark",
        "path": "results/gold/day4/manifest.json",
        "kind": "day4",
    },
    {
        "key": "day6_planner",
        "label": "Typed query planning",
        "path": "results/day6/planner_validation.json",
        "kind": "standard",
    },
    {
        "key": "day7_sql_generation",
        "label": "Parameterized SQL generation",
        "path": "results/day7/sql_generation_validation.json",
        "kind": "standard",
    },
    {
        "key": "day8_ast",
        "label": "AST safety validation",
        "path": "results/day8/ast_validation.json",
        "kind": "standard",
    },
    {
        "key": "day8_execution",
        "label": "Restricted read-only execution",
        "path": "results/day8/execution_validation.json",
        "kind": "standard",
        "latency_field": "elapsed_ms",
    },
    {
        "key": "day9_agent",
        "label": "Agent routing and tool-use reliability",
        "path": "results/day9/agent_validation.json",
        "kind": "standard",
        "latency_field": "total_elapsed_ms",
    },
    {
        "key": "day10_vector",
        "label": "Semantic and hybrid vector retrieval",
        "path": "results/day10/vector_validation.json",
        "kind": "standard",
    },
    {
        "key": "day11_llm",
        "label": "OpenAI structured planning",
        "path": "results/day11/llm_validation.json",
        "kind": "standard",
        "latency_field": "total_elapsed_ms",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Generate a partial report when benchmark artifacts are missing.",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Skip the live database snapshot (development only).",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return round(ordered[index], 3)


def summarize_standard(spec: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    cases_value = payload.get("cases")
    if isinstance(cases_value, list):
        case_rows = cases_value
    elif isinstance(payload.get("results"), list):
        case_rows = payload["results"]
    else:
        case_rows = []
    total = int(payload.get("total", payload.get("cases", len(case_rows))))
    passed = int(payload.get("passed", sum(bool(row.get("passed")) for row in case_rows)))
    rate = payload.get("accuracy", payload.get("pass_rate"))
    if rate is None:
        rate = passed / total if total else 0.0

    latency_field = spec.get("latency_field")
    latencies: list[float] = []
    if latency_field:
        for row in case_rows:
            value = row.get(latency_field)
            if isinstance(value, (int, float)):
                latencies.append(float(value))

    return {
        "key": spec["key"],
        "label": spec["label"],
        "source": spec["path"],
        "passed": passed,
        "total": total,
        "pass_rate": round(float(rate), 4),
        "mean_latency_ms": (
            round(statistics.mean(latencies), 3) if latencies else None
        ),
        "p95_latency_ms": p95(latencies),
    }


def summarize_day4(spec: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("queries", [])
    passed = sum(
        int(
            int(item.get("row_count", -1))
            == int(item.get("expected_row_count", -2))
        )
        for item in rows
    )
    total = len(rows)
    latencies = [
        float(item["execution_ms"])
        for item in rows
        if isinstance(item.get("execution_ms"), (int, float))
    ]
    succeeded = payload.get("status") == "succeeded" and not payload.get("failures")
    if not succeeded:
        passed = min(passed, max(0, total - 1))

    return {
        "key": spec["key"],
        "label": spec["label"],
        "source": spec["path"],
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "mean_latency_ms": (
            round(statistics.mean(latencies), 3) if latencies else None
        ),
        "p95_latency_ms": p95(latencies),
    }


def load_benchmarks(allow_missing: bool) -> tuple[list[dict[str, Any]], list[str]]:
    summaries: list[dict[str, Any]] = []
    missing: list[str] = []

    for spec in BENCHMARK_SPECS:
        path = PROJECT_ROOT / spec["path"]
        if not path.exists():
            missing.append(spec["path"])
            continue
        payload = read_json(path)
        summary = (
            summarize_day4(spec, payload)
            if spec["kind"] == "day4"
            else summarize_standard(spec, payload)
        )
        summaries.append(summary)

    if missing and not allow_missing:
        formatted = "\n".join(f"- {item}" for item in missing)
        raise SystemExit(
            "Required benchmark artifacts are missing:\n"
            f"{formatted}\n"
            "Run the corresponding validation scripts, then rerun Day 12."
        )
    return summaries, missing


def database_snapshot() -> tuple[dict[str, Any], dict[str, Any]]:
    settings = get_settings()
    connection = open_db_connection(settings)
    try:
        connection.execute("SET TRANSACTION READ ONLY")
        counts = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM core.neighborhoods) AS neighborhoods,
                (SELECT COUNT(*) FROM core.parks) AS parks,
                (SELECT COUNT(*) FROM core.schools) AS schools,
                (
                    SELECT COUNT(*)
                    FROM app.san_jose_active_schools_spatial
                ) AS schools_in_scope,
                (
                    SELECT COUNT(*)
                    FROM core.parks
                    WHERE current_status = 'Open'
                ) AS open_park_features,
                (
                    SELECT COUNT(DISTINCT (entity_type, entity_id))
                    FROM semantic.entity_documents
                ) AS semantic_documents,
                (
                    SELECT COUNT(*)
                    FROM semantic.entity_documents
                ) AS embedded_vectors
            """
        ).fetchone()
        assert counts is not None

        model_rows = connection.execute(
            """
            SELECT embedding_model, COUNT(*)::integer AS document_count
            FROM semantic.entity_documents
            GROUP BY embedding_model
            ORDER BY embedding_model
            """
        ).fetchall()
        embedding_models = {
            str(row["embedding_model"]): int(row["document_count"])
            for row in model_rows
        }

        versions = connection.execute(
            """
            SELECT
                current_setting('server_version') AS postgresql_version,
                PostGIS_Version() AS postgis_version,
                (
                    SELECT extversion
                    FROM pg_extension
                    WHERE extname = 'vector'
                ) AS pgvector_version,
                EXISTS (
                    SELECT 1
                    FROM pg_indexes
                    WHERE schemaname = 'semantic'
                      AND indexname = 'idx_entity_documents_embedding_hnsw'
                ) AS hnsw_index_present
            """
        ).fetchone()
        assert versions is not None

        snapshot = {
            "neighborhoods": int(counts["neighborhoods"]),
            "parks": int(counts["parks"]),
            "schools": int(counts["schools"]),
            "schools_in_scope": int(counts["schools_in_scope"]),
            "open_park_features": int(counts["open_park_features"]),
            "semantic_documents": int(counts["semantic_documents"]),
            "embedded_vectors": int(counts["embedded_vectors"]),
            "embedding_models": embedding_models,
        }
        database = {
            "postgresql_version": str(versions["postgresql_version"]),
            "postgis_version": str(versions["postgis_version"]),
            "pgvector_version": str(versions["pgvector_version"]),
            "hnsw_index_present": bool(versions["hnsw_index_present"]),
            "execution_role": settings.copilot_execution_role,
        }
        return snapshot, database
    finally:
        connection.rollback()
        connection.close()


def llm_metrics() -> dict[str, Any] | None:
    path = PROJECT_ROOT / "results/day11/llm_validation.json"
    if not path.exists():
        return None
    payload = read_json(path)
    return {
        "model": payload.get("model"),
        "intent_accuracy": payload.get("llm_intent_accuracy"),
        "deterministic_intent_accuracy": payload.get(
            "deterministic_intent_accuracy"
        ),
        "input_tokens": int(payload.get("input_tokens", 0)),
        "output_tokens": int(payload.get("output_tokens", 0)),
        "estimated_cost_usd": payload.get("estimated_cost_usd"),
    }


def embedding_comparison() -> dict[str, Any] | None:
    path = PROJECT_ROOT / "results/day11/embedding_comparison.json"
    if not path.exists():
        return None
    payload = read_json(path)
    rows = payload.get("results", [])
    if not rows:
        return None

    def mean_field(name: str) -> float | None:
        values = [
            float(row[name])
            for row in rows
            if isinstance(row.get(name), (int, float))
        ]
        return round(statistics.mean(values), 3) if values else None

    return {
        "case_count": len(rows),
        "mean_overlap_at_10": mean_field("overlap_at_10"),
        "mean_jaccard_at_10": mean_field("jaccard_at_10"),
        "local_mean_latency_ms": mean_field("local_elapsed_ms"),
        "openai_mean_latency_ms": mean_field("openai_elapsed_ms"),
    }


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    output = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    output.extend(
        "| " + " | ".join(str(value) for value in row) + " |"
        for row in rows
    )
    return "\n".join(output)


def percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.1f}%"


def build_report(metrics: dict[str, Any]) -> str:
    benchmark_rows = [
        [
            item["label"],
            f"{item['passed']}/{item['total']}",
            percent(item["pass_rate"]),
            item["mean_latency_ms"] if item["mean_latency_ms"] is not None else "—",
            item["p95_latency_ms"] if item["p95_latency_ms"] is not None else "—",
        ]
        for item in metrics["benchmarks"]
    ]
    snapshot = metrics.get("data_snapshot") or {}
    db = metrics.get("database") or {}
    llm = metrics.get("llm") or {}
    comparison = metrics.get("embedding_comparison") or {}

    return f"""# AgenticDB-SJ Final Technical Report

Generated: `{metrics['generated_at']}`  
Version: `{metrics['version']}`

## Executive summary

AgenticDB-SJ is a provenance-aware natural-language database copilot over
real public relational, geospatial, and vector data. It combines PostgreSQL,
PostGIS, pgvector, FastAPI, OpenAI structured planning, deterministic
parameterized SQL templates, independent SQLGlot AST validation, restricted
read-only execution, and row-level evidence.

The final release aggregated **{metrics['aggregate_total']} benchmark checks**
across {metrics['benchmark_count']} validation suites, with an aggregate pass
rate of **{percent(metrics['aggregate_pass_rate'])}**.

## Data snapshot

- Neighborhood polygons: **{snapshot.get('neighborhoods', 'N/A')}**
- Park-source features: **{snapshot.get('parks', 'N/A')}**
- Active school records: **{snapshot.get('schools', 'N/A')}**
- Schools in San José spatial scope: **{snapshot.get('schools_in_scope', 'N/A')}**
- Distinct semantic documents: **{snapshot.get('semantic_documents', 'N/A')}**
- Stored embedding vectors: **{snapshot.get('embedded_vectors', 'N/A')}**
- Embedding models stored: **{len(snapshot.get('embedding_models', {}))}**

## Evaluation

{markdown_table(
    ['Benchmark', 'Passed', 'Pass rate', 'Mean ms', 'P95 ms'],
    benchmark_rows,
)}

## Database and retrieval stack

- PostgreSQL: `{db.get('postgresql_version', 'N/A')}`
- PostGIS: `{db.get('postgis_version', 'N/A')}`
- pgvector: `{db.get('pgvector_version', 'N/A')}`
- HNSW index present: `{db.get('hnsw_index_present', 'N/A')}`
- Restricted execution role: `{db.get('execution_role', 'N/A')}`

## Hosted-model evaluation

- Model: `{llm.get('model', 'N/A')}`
- LLM intent accuracy: **{percent(llm.get('intent_accuracy'))}**
- Deterministic baseline intent accuracy: **{percent(llm.get('deterministic_intent_accuracy'))}**
- Input tokens: **{llm.get('input_tokens', 0)}**
- Output tokens: **{llm.get('output_tokens', 0)}**
- Estimated benchmark cost: **{llm.get('estimated_cost_usd', 'not configured')}**

## Embedding-provider comparison

- Cases: **{comparison.get('case_count', 0)}**
- Mean overlap@10: **{comparison.get('mean_overlap_at_10', 'N/A')}**
- Mean Jaccard@10: **{comparison.get('mean_jaccard_at_10', 'N/A')}**
- Local mean latency: **{comparison.get('local_mean_latency_ms', 'N/A')} ms**
- OpenAI mean latency: **{comparison.get('openai_mean_latency_ms', 'N/A')} ms**

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
"""


def build_cv_bullets(metrics: dict[str, Any]) -> str:
    snapshot = metrics.get("data_snapshot") or {}
    llm = metrics.get("llm") or {}
    total_records = (
        int(snapshot.get("neighborhoods", 0))
        + int(snapshot.get("parks", 0))
        + int(snapshot.get("schools", 0))
    )
    return f"""# CV-Ready AgenticDB-SJ Bullets

Use only after the generated metrics have been reviewed.

## Detailed version

- Built AgenticDB-SJ, a provenance-aware natural-language database copilot over
  **{total_records:,} real public records**, using PostgreSQL, PostGIS, pgvector,
  FastAPI, Python, and OpenAI structured planning for relational, spatial,
  semantic, and hybrid retrieval.
- Implemented allowlisted schema retrieval, deterministic parameterized SQL,
  SQLGlot AST validation, bounded result policies, and restricted read-only
  PostgreSQL execution with query fingerprints and row-level evidence.
- Indexed **{snapshot.get('semantic_documents', 0):,} distinct source-derived
  documents** as **{snapshot.get('embedded_vectors', 0):,} stored vectors** with
  384-dimensional embeddings and HNSW cosine search, supporting local MiniLM
  and hosted OpenAI embedding providers through configuration.
- Evaluated planning, SQL generation, adversarial safety, execution, agent
  routing, vector retrieval, and hosted-model planning across
  **{metrics['aggregate_total']} benchmark checks**, achieving an aggregate
  pass rate of **{percent(metrics['aggregate_pass_rate'])}**.
- Compared hosted and deterministic planning on the same benchmark;
  hosted-model intent accuracy was **{percent(llm.get('intent_accuracy'))}**
  and the deterministic baseline was
  **{percent(llm.get('deterministic_intent_accuracy'))}**.

## Two-bullet resume version

- Built a natural-language database copilot over **{total_records:,} real public
  records** using PostgreSQL, PostGIS, pgvector, FastAPI, and OpenAI structured
  planning, supporting relational, spatial, semantic, and hybrid retrieval.
- Implemented parameterized SQL generation, independent AST guardrails,
  restricted read-only execution, HNSW vector search, evidence-backed answers,
  and an evaluation suite with **{metrics['aggregate_total']} benchmark checks**
  at **{percent(metrics['aggregate_pass_rate'])}** aggregate pass rate.

## One-line version

Developed a provenance-aware database copilot using PostgreSQL/PostGIS,
pgvector, FastAPI, and OpenAI structured planning, with safe SQL execution,
hybrid retrieval, and benchmarked tool-use reliability.
"""


def metrics_block(metrics: dict[str, Any]) -> str:
    rows = "\n".join(
        f"| {item['label']} | {item['passed']}/{item['total']} | "
        f"{percent(item['pass_rate'])} |"
        for item in metrics["benchmarks"]
    )
    return f"""<!-- DAY12_METRICS_START -->
## Measured v1.0 results

| Evaluation suite | Passed | Pass rate |
| --- | ---: | ---: |
{rows}

**Aggregate:** {metrics['aggregate_passed']}/{metrics['aggregate_total']}
benchmark checks passed ({percent(metrics['aggregate_pass_rate'])}).

The complete generated report is in
[`docs/FINAL_REPORT.md`](docs/FINAL_REPORT.md).
<!-- DAY12_METRICS_END -->"""


def update_readme(metrics: dict[str, Any]) -> None:
    text = README_PATH.read_text(encoding="utf-8")
    start = "<!-- DAY12_METRICS_START -->"
    end = "<!-- DAY12_METRICS_END -->"
    block = metrics_block(metrics)
    if start in text and end in text:
        before = text.split(start, 1)[0]
        after = text.split(end, 1)[1]
        text = before + block + after
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    README_PATH.write_text(text, encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(benchmarks: list[dict[str, Any]]) -> None:
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "key",
                "label",
                "source",
                "passed",
                "total",
                "pass_rate",
                "mean_latency_ms",
                "p95_latency_ms",
            ],
        )
        writer.writeheader()
        writer.writerows(benchmarks)


def build_manifest() -> dict[str, Any]:
    artifact_paths = [
        README_PATH,
        FINAL_REPORT_PATH,
        CV_BULLETS_PATH,
        METRICS_PATH,
        CSV_PATH,
        PROJECT_ROOT / "docs/ARCHITECTURE.md",
        PROJECT_ROOT / "CHANGELOG.md",
        PROJECT_ROOT / "CITATION.cff",
    ]
    return {
        "status": "ready",
        "version": __version__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": [
            {
                "path": str(path.relative_to(PROJECT_ROOT)),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in artifact_paths
            if path.exists()
        ],
    }


def main() -> None:
    args = parse_args()
    benchmarks, missing = load_benchmarks(args.allow_missing)

    if args.skip_db:
        snapshot = None
        database = None
    else:
        snapshot, database = database_snapshot()

    aggregate_passed = sum(item["passed"] for item in benchmarks)
    aggregate_total = sum(item["total"] for item in benchmarks)
    aggregate_rate = (
        aggregate_passed / aggregate_total if aggregate_total else 0.0
    )
    all_passed = bool(benchmarks) and all(
        item["passed"] == item["total"] for item in benchmarks
    )

    generated_at = datetime.now(timezone.utc).isoformat()
    metrics = {
        "status": "ready" if not missing else "not_built",
        "project": "AgenticDB-SJ",
        "version": __version__,
        "generated_at": generated_at,
        "all_benchmarks_passed": all_passed,
        "benchmark_count": len(benchmarks),
        "aggregate_passed": aggregate_passed,
        "aggregate_total": aggregate_total,
        "aggregate_pass_rate": round(aggregate_rate, 4),
        "benchmarks": benchmarks,
        "data_snapshot": snapshot,
        "database": database,
        "llm": llm_metrics(),
        "embedding_comparison": embedding_comparison(),
        "artifacts": {
            "final_report": "docs/FINAL_REPORT.md",
            "cv_bullets": "docs/CV_BULLETS.md",
            "architecture": "docs/ARCHITECTURE.md",
            "benchmark_csv": "results/day12/benchmark_summary.csv",
            "manifest": "results/day12/release_manifest.json",
        },
        "notes": (
            [f"Missing optional/required artifact: {item}" for item in missing]
            if missing
            else [
                "All values were aggregated from committed benchmark artifacts "
                "and the live read-only database snapshot."
            ]
        ),
        "extra_metrics": {},
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    write_csv(benchmarks)
    FINAL_REPORT_PATH.write_text(build_report(metrics), encoding="utf-8")
    CV_BULLETS_PATH.write_text(build_cv_bullets(metrics), encoding="utf-8")
    update_readme(metrics)

    manifest = build_manifest()
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"Release metrics: {aggregate_passed}/{aggregate_total} checks passed "
        f"({aggregate_rate:.1%})"
    )
    print(f"Wrote {METRICS_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {FINAL_REPORT_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {CV_BULLETS_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {MANIFEST_PATH.relative_to(PROJECT_ROOT)}")

    if not all_passed and not args.allow_missing:
        raise SystemExit("Release generation completed, but not every benchmark passed.")


if __name__ == "__main__":
    main()
