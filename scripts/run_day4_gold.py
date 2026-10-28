#!/usr/bin/env python3
"""Execute the ten trusted Day 4 SQL queries and export deterministic gold CSVs."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = PROJECT_ROOT / "benchmarks" / "day4" / "query_catalog.json"
OUTPUT_DIR = PROJECT_ROOT / "results" / "gold" / "day4"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def serialize(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def connection_kwargs() -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env")
    required = ["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_PORT"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing required .env values: {', '.join(missing)}")

    return {
        "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "port": int(os.environ["POSTGRES_PORT"]),
        "dbname": os.environ["POSTGRES_DB"],
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
        "row_factory": dict_row,
    }


def fetch_snapshot_counts(conn: psycopg.Connection) -> dict[str, int]:
    sql = """
    SELECT
        (SELECT COUNT(*) FROM core.neighborhoods) AS neighborhoods,
        (SELECT COUNT(*) FROM core.parks) AS parks,
        (SELECT COUNT(*) FROM core.schools) AS schools,
        (SELECT COUNT(*) FROM app.san_jose_active_schools_spatial) AS schools_in_scope,
        (SELECT COUNT(*) FROM core.parks WHERE current_status = 'Open') AS open_park_features
    """
    row = conn.execute(sql).fetchone()
    assert row is not None
    return {key: int(value) for key, value in row.items()}


def main() -> int:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "benchmark_name": catalog["benchmark_name"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "catalog": str(CATALOG_PATH.relative_to(PROJECT_ROOT)),
        "queries": [],
    }

    failures: list[str] = []

    with psycopg.connect(**connection_kwargs()) as conn:
        with conn.transaction():
            conn.execute("SET TRANSACTION READ ONLY")
            conn.execute("SET LOCAL statement_timeout = '60s'")

            snapshot_counts = fetch_snapshot_counts(conn)
            manifest["snapshot_counts"] = snapshot_counts
            required_counts = {
                "neighborhoods": 297,
                "parks": 611,
                "schools": 10537,
                "schools_in_scope": 220,
                "open_park_features": 526,
            }
            for key, expected in required_counts.items():
                actual = snapshot_counts.get(key)
                if actual != expected:
                    failures.append(
                        f"Snapshot count mismatch for {key}: expected {expected}, got {actual}"
                    )

            for item in catalog["queries"]:
                query_id = item["id"]
                sql_path = PROJECT_ROOT / item["sql_file"]
                sql = sql_path.read_text(encoding="utf-8")

                started = time.perf_counter()
                with conn.cursor() as cur:
                    cur.execute(sql)
                    rows = cur.fetchall()
                    columns = [desc.name for desc in cur.description or []]
                elapsed_ms = round((time.perf_counter() - started) * 1000, 3)

                expected_columns = item["expected_columns"]
                if columns != expected_columns:
                    failures.append(
                        f"{query_id}: columns differ. Expected {expected_columns}, got {columns}"
                    )

                expected_rows = int(item["expected_rows"])
                if len(rows) != expected_rows:
                    failures.append(
                        f"{query_id}: expected {expected_rows} rows, got {len(rows)}"
                    )

                csv_path = OUTPUT_DIR / f"{query_id}.csv"
                with csv_path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=columns)
                    writer.writeheader()
                    for row in rows:
                        writer.writerow({key: serialize(row[key]) for key in columns})

                manifest["queries"].append(
                    {
                        "id": query_id,
                        "question": item["question"],
                        "sql_file": item["sql_file"],
                        "csv_file": str(csv_path.relative_to(PROJECT_ROOT)),
                        "row_count": len(rows),
                        "expected_row_count": expected_rows,
                        "columns": columns,
                        "execution_ms": elapsed_ms,
                        "sha256": sha256_file(csv_path),
                    }
                )
                print(f"{query_id}: {len(rows):>3} rows | {elapsed_ms:>9.3f} ms | {csv_path}")

    manifest["status"] = "failed" if failures else "succeeded"
    manifest["failures"] = failures
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if failures:
        print("\nDay 4 export completed with validation failures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        print(f"Manifest: {manifest_path}", file=sys.stderr)
        return 1

    print(f"\nAll ten gold queries matched the fixed-snapshot expectations.")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
