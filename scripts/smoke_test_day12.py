#!/usr/bin/env python3
"""Live smoke test for the final v1.0 demo and release endpoints."""

from __future__ import annotations

import json
import urllib.request


BASE_URL = "http://127.0.0.1:8000"


def request(method: str, path: str, payload: dict | None = None):
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        BASE_URL + path,
        data=body,
        method=method,
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        raw = response.read().decode("utf-8")
        content_type = response.headers.get("content-type", "")
        return response.status, (
            json.loads(raw) if "application/json" in content_type else raw
        )


def main() -> None:
    status, live = request("GET", "/health/live")
    assert status == 200 and live["status"] == "ok"
    print("PASS /health/live")

    status, demo = request("GET", "/demo")
    assert status == 200 and "AgenticDB-SJ" in demo
    print("PASS /demo")

    status, metrics = request("GET", "/api/v1/release/metrics")
    assert status == 200 and metrics["status"] == "ready"
    assert metrics["all_benchmarks_passed"] is True
    print("PASS /api/v1/release/metrics")

    status, run = request(
        "POST",
        "/api/v1/copilot/llm/run",
        {
            "question": (
                "Which neighborhoods contain at least three active schools "
                "and two open park features?"
            ),
            "provider": "deterministic",
            "evidence_limit": 3,
        },
    )
    assert status == 200
    assert run["run"]["status"] == "completed"
    assert run["run"]["execution"]["row_count"] == 15
    assert run["run"]["execution"]["transaction_read_only"] is True
    print("PASS deterministic end-to-end query")

    print("Day 12 release smoke test PASSED")


if __name__ == "__main__":
    main()
