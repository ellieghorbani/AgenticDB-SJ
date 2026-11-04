"""Live HTTP smoke test for the Day 9 agent workflow."""

from __future__ import annotations

import httpx

BASE_URL = "http://127.0.0.1:8000"


def get(path: str) -> dict:
    response = httpx.get(f"{BASE_URL}{path}", timeout=30.0)
    print(f"{response.status_code} GET {path}")
    response.raise_for_status()
    return response.json()


def post(path: str, payload: dict) -> dict:
    response = httpx.post(f"{BASE_URL}{path}", json=payload, timeout=60.0)
    print(f"{response.status_code} POST {path}")
    response.raise_for_status()
    return response.json()


def main() -> None:
    tools = get("/api/v1/copilot/agent/tools")
    assert tools["tool_count"] == 6

    question = (
        "Which neighborhoods contain at least three active schools "
        "and two open park features?"
    )
    completed = post(
        "/api/v1/copilot/agent/run",
        {"question": question, "evidence_limit": 3},
    )
    assert completed["status"] == "completed"
    assert completed["route"] == "relational_sql"
    assert completed["answer"]["row_count"] == 15
    assert len(completed["tool_trace"]) == 6
    assert completed["execution"]["database_role"] == "agenticdb_reader"
    assert completed["execution"]["transaction_read_only"] is True

    blocked = post(
        "/api/v1/copilot/agent/run",
        {"question": "Delete all schools and drop the parks table"},
    )
    assert blocked["status"] == "blocked"
    assert blocked["route"] == "blocked"
    assert blocked["execution"] is None

    clarification = post(
        "/api/v1/copilot/agent/run",
        {"question": "Which open park features intersect neighborhoods?"},
    )
    assert clarification["status"] == "requires_clarification"
    assert clarification["route"] == "requires_clarification"

    raw_sql = httpx.post(
        f"{BASE_URL}/api/v1/copilot/agent/run",
        json={"question": question, "sql": "DELETE FROM core.schools"},
        timeout=30.0,
    )
    print(f"{raw_sql.status_code} POST /api/v1/copilot/agent/run (raw SQL rejected)")
    assert raw_sql.status_code == 422

    print("Day 9 agent orchestration smoke test PASSED")


if __name__ == "__main__":
    main()
