#!/usr/bin/env python3
"""Validate the generated AgenticDB-SJ v1.0 release artifacts."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import __version__


METRICS = PROJECT_ROOT / "results/day12/final_evaluation.json"
MANIFEST = PROJECT_ROOT / "results/day12/release_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    checks: list[tuple[str, bool, str]] = []

    checks.append(("metrics_exist", METRICS.exists(), str(METRICS)))
    checks.append(("manifest_exists", MANIFEST.exists(), str(MANIFEST)))
    if not METRICS.exists() or not MANIFEST.exists():
        for name, passed, detail in checks:
            print(f"{'PASS' if passed else 'FAIL'} {name}: {detail}")
        raise SystemExit(1)

    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    checks.extend(
        [
            (
                "release_status",
                metrics.get("status") == "ready",
                str(metrics.get("status")),
            ),
            (
                "release_version",
                metrics.get("version") == __version__ == "1.0.0",
                f"metrics={metrics.get('version')} app={__version__}",
            ),
            (
                "all_benchmarks_passed",
                metrics.get("all_benchmarks_passed") is True,
                (
                    f"{metrics.get('aggregate_passed')}/"
                    f"{metrics.get('aggregate_total')}"
                ),
            ),
            (
                "benchmark_coverage",
                int(metrics.get("benchmark_count", 0)) >= 8,
                str(metrics.get("benchmark_count")),
            ),
            (
                "database_snapshot",
                bool(metrics.get("data_snapshot")),
                "live snapshot present",
            ),
            (
                "semantic_documents",
                int((metrics.get("data_snapshot") or {}).get(
                    "semantic_documents",
                    0,
                )) >= 1128,
                str((metrics.get("data_snapshot") or {}).get(
                    "semantic_documents"
                )),
            ),
            (
                "embedded_vectors",
                int((metrics.get("data_snapshot") or {}).get(
                    "embedded_vectors",
                    0,
                )) >= int((metrics.get("data_snapshot") or {}).get(
                    "semantic_documents",
                    0,
                )),
                str((metrics.get("data_snapshot") or {}).get(
                    "embedded_vectors"
                )),
            ),
            (
                "hnsw_index",
                (metrics.get("database") or {}).get(
                    "hnsw_index_present"
                ) is True,
                str((metrics.get("database") or {}).get(
                    "hnsw_index_present"
                )),
            ),
        ]
    )

    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    checks.append(
        (
            "readme_metrics",
            "<!-- DAY12_METRICS_START -->" in readme
            and "Measured v1.0 results" in readme,
            "README metrics block",
        )
    )

    for item in manifest.get("files", []):
        path = PROJECT_ROOT / item["path"]
        passed = path.exists() and sha256(path) == item["sha256"]
        checks.append(
            (
                f"checksum:{item['path']}",
                passed,
                item["sha256"],
            )
        )

    try:
        tracked = subprocess.run(
            ["git", "ls-files"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        secret_safe = ".env" not in tracked and not any(
            item.endswith("/.env") for item in tracked
        )
        checks.append(("env_not_tracked", secret_safe, "git ls-files"))
    except (subprocess.CalledProcessError, FileNotFoundError):
        checks.append(("env_not_tracked", True, "git unavailable; skipped"))

    failed = 0
    for name, passed, detail in checks:
        print(f"{'PASS' if passed else 'FAIL'} {name}: {detail}")
        failed += int(not passed)

    print(f"\nDay 12 release validation: {len(checks)-failed}/{len(checks)} passed")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
