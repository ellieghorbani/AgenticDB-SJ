#!/usr/bin/env python3
"""Validate Day 4 gold CSV invariants independently of PostgreSQL execution."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = PROJECT_ROOT / "benchmarks" / "day4" / "query_catalog.json"
RESULT_DIR = PROJECT_ROOT / "results" / "gold" / "day4"


def read_csv(query_id: str) -> tuple[list[str], list[dict[str, str]]]:
    path = RESULT_DIR / f"{query_id}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing result file: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def as_int(value: str) -> int:
    return int(value or 0)


def as_float(value: str) -> float:
    return float(value or 0.0)


def main() -> int:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    data: dict[str, list[dict[str, str]]] = {}

    for item in catalog["queries"]:
        query_id = item["id"]
        try:
            columns, rows = read_csv(query_id)
        except Exception as exc:
            errors.append(f"{query_id}: {exc}")
            continue

        data[query_id] = rows
        if columns != item["expected_columns"]:
            errors.append(f"{query_id}: unexpected columns {columns}")
        if len(rows) != int(item["expected_rows"]):
            errors.append(
                f"{query_id}: expected {item['expected_rows']} rows, found {len(rows)}"
            )

    if "q01" in data:
        rows = data["q01"]
        if sum(as_int(r["active_school_count"]) for r in rows) != 220:
            errors.append("q01: neighborhood school counts do not sum to 220")
        if len({r["neighborhood_id"] for r in rows}) != len(rows):
            errors.append("q01: duplicate neighborhood IDs")

    if "q02" in data:
        rows = data["q02"]
        if sum(as_int(r["open_park_feature_count"]) for r in rows) != 609:
            errors.append("q02: park-neighborhood intersection counts do not sum to 609")

    if "q03" in data:
        rows = data["q03"]
        if len({r["cds_code"] for r in rows}) != len(rows):
            errors.append("q03: duplicate school IDs")
        if any(as_float(r["distance_meters"]) > 1609.344 for r in rows):
            errors.append("q03: result contains a school farther than one mile")

    if "q04" in data:
        rows = data["q04"]
        if len({r["cds_code"] for r in rows}) != 220:
            errors.append("q04: expected one nearest-park row for each of 220 schools")
        if any(as_float(r["distance_meters"]) < 0 for r in rows):
            errors.append("q04: negative distance found")

    if "q05" in data:
        rows = data["q05"]
        if any(r["neighborhood_id"] != "REF-NEIG-0000000194" for r in rows):
            errors.append("q05: a row belongs to the wrong neighborhood")

    if "q06" in data:
        for row in data["q06"]:
            if as_int(row["active_school_count"]) < 3:
                errors.append("q06: active_school_count below 3")
            if as_int(row["open_park_feature_count"]) < 2:
                errors.append("q06: open_park_feature_count below 2")

    if "q07" in data and data["q07"]:
        errors.append("q07: expected a valid zero-row result for this snapshot")

    if "q08" in data:
        rows = data["q08"]
        if sum(as_int(r["active_school_count"]) for r in rows) != 220:
            errors.append("q08: grouped active_school_count does not sum to 220")
        for row in rows:
            minimum = as_float(row["minimum_nearest_park_distance_m"])
            average = as_float(row["average_nearest_park_distance_m"])
            maximum = as_float(row["maximum_nearest_park_distance_m"])
            if not minimum <= average <= maximum:
                errors.append(f"q08: invalid min/average/max ordering for {row['neighborhood_id']}")

    if "q09" in data:
        counts = [as_int(r["active_school_count_within_one_mile"]) for r in data["q09"]]
        if counts != sorted(counts, reverse=True):
            errors.append("q09: result is not ordered by descending school count")
        if counts and counts[0] != 22:
            errors.append(f"q09: expected maximum nearby-school count 22, found {counts[0]}")

    if "q10" in data:
        for row in data["q10"]:
            if as_int(row["elementary_school_count"]) < 1:
                errors.append("q10: neighborhood lacks an elementary school")
            if as_int(row["high_school_count"]) < 1:
                errors.append("q10: neighborhood lacks a high school")

    if errors:
        print("Day 4 gold-result validation FAILED:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Day 4 gold-result validation PASSED")
    print("Validated 10 CSV files and all cross-query invariants.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
