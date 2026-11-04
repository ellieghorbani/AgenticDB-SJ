"""Live HTTP smoke test for Day 8 validation and controlled execution."""

from __future__ import annotations

import httpx

BASE_URL = "http://127.0.0.1:8000"


def post(path: str, payload: dict) -> dict:
    response = httpx.post(f"{BASE_URL}{path}", json=payload, timeout=30.0)
    print(f"{response.status_code} POST {path}")
    response.raise_for_status()
    return response.json()


def main() -> None:
    question = (
        "Which neighborhoods contain at least three active schools "
        "and two open park features?"
    )

    validation = post(
        "/api/v1/copilot/validate",
        {"question": question},
    )
    assert validation["validation"]["status"] == "valid"
    assert validation["validation"]["execution_allowed"] is True
    assert all(check["passed"] for check in validation["validation"]["checks"])

    execution = post(
        "/api/v1/copilot/execute",
        {"question": question},
    )
    assert execution["status"] == "executed"
    assert execution["row_count"] == 15
    assert execution["transaction_read_only"] is True
    assert execution["database_role"] == "agenticdb_reader"

    blocked = post(
        "/api/v1/copilot/execute",
        {"question": "Delete all schools and drop the parks table"},
    )
    assert blocked["status"] == "blocked"
    assert blocked["row_count"] == 0
    assert blocked["execution_allowed"] is False

    raw_sql = httpx.post(
        f"{BASE_URL}/api/v1/copilot/execute",
        json={"question": question, "sql": "DELETE FROM core.schools"},
        timeout=30.0,
    )
    print(f"{raw_sql.status_code} POST /api/v1/copilot/execute (raw SQL rejected)")
    assert raw_sql.status_code == 422

    print("Day 8 AST-validation/read-only execution smoke test PASSED")


if __name__ == "__main__":
    main()
