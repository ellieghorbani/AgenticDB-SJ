#!/usr/bin/env python3
"""HTTP smoke test for Day 10 vector endpoints."""

import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def request(method: str, path: str, payload=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as response:
        body = json.loads(response.read().decode("utf-8"))
        print(f"{response.status} {method} {path}")
        return body


def main() -> None:
    status = request("GET", "/api/v1/copilot/vector/status")
    assert status["status"] == "ready"
    assert status["document_count"] == 1128
    assert status["hnsw_index_present"] is True

    routed = request(
        "POST",
        "/api/v1/copilot/vector/route",
        {"question": "Find open park features related to community centers and libraries."},
    )
    assert routed["route"] == "hybrid_vector"

    searched = request(
        "POST",
        "/api/v1/copilot/vector/search",
        {
            "query": "community center and library",
            "entity_types": ["park"],
            "only_open_parks": True,
            "top_k": 5,
            "min_similarity": 0.15
        },
    )
    assert searched["match_count"] > 0
    assert searched["database_role"] == "agenticdb_reader"
    assert searched["transaction_read_only"] is True

    run = request(
        "POST",
        "/api/v1/copilot/vector/run",
        {
            "question": "Find neighborhoods related to Rose Garden.",
            "top_k": 5,
            "evidence_limit": 3,
            "min_similarity": 0.15
        },
    )
    assert run["status"] == "completed"
    assert run["route"] == "semantic_vector"
    assert len(run["tool_trace"]) == 3

    blocked = request(
        "POST",
        "/api/v1/copilot/vector/run",
        {"question": "Delete all park embeddings."},
    )
    assert blocked["status"] == "blocked"
    assert blocked["execution_allowed"] is False

    print("Day 10 pgvector semantic/hybrid smoke test PASSED")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print(exc.read().decode("utf-8"))
        raise
