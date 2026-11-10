#!/usr/bin/env python3
"""HTTP smoke test for Day 11 OpenAI-assisted planning and execution."""

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
    with urllib.request.urlopen(req, timeout=120) as response:
        body = json.loads(response.read().decode("utf-8"))
        print(f"{response.status} {method} {path}")
        return body


def main() -> None:
    status = request("GET", "/api/v1/copilot/llm/status")
    assert status["status"] == "ready"
    assert status["openai_api_key_configured"] is True

    planned = request(
        "POST",
        "/api/v1/copilot/llm/plan",
        {
            "question": "Find neighborhoods with three schools and two parks.",
            "provider": "openai",
        },
    )
    assert planned["provider_used"] == "openai"
    assert planned["plan"]["intent"] == (
        "neighborhoods_with_minimum_schools_and_parks"
    )
    assert planned["usage"]["api_called"] is True

    run = request(
        "POST",
        "/api/v1/copilot/llm/run",
        {
            "question": "Find neighborhoods with three schools and two parks.",
            "provider": "openai",
            "evidence_limit": 2,
        },
    )
    assert run["planning"]["provider_used"] == "openai"
    assert run["run"]["status"] == "completed"
    assert run["run"]["execution"]["database_role"] == "agenticdb_reader"
    assert run["run"]["execution"]["transaction_read_only"] is True

    blocked = request(
        "POST",
        "/api/v1/copilot/llm/run",
        {
            "question": "Delete all schools and drop the parks table.",
            "provider": "openai",
        },
    )
    assert blocked["planning"]["provider_used"] == "local_safety_gate"
    assert blocked["planning"]["usage"]["api_called"] is False
    assert blocked["run"]["status"] == "blocked"

    print("Day 11 OpenAI-assisted copilot smoke test PASSED")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print(exc.read().decode("utf-8"))
        raise
