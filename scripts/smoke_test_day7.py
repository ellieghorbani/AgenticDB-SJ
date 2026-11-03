"""Live HTTP smoke test for Day 7 SQL generation."""

from __future__ import annotations

import os

import httpx

BASE_URL = os.getenv("AGENTICDB_API_URL", "http://127.0.0.1:8000")


def post(question: str) -> dict:
    response = httpx.post(
        f"{BASE_URL}/api/v1/copilot/sql",
        json={"question": question},
        timeout=15.0,
    )
    print(f"{response.status_code} POST /api/v1/copilot/sql")
    response.raise_for_status()
    return response.json()


def main() -> None:
    generated = post(
        "Which neighborhoods contain at least three active schools "
        "and two open park features?"
    )
    assert generated["status"] == "generated"
    assert generated["sql_generated"] is True
    assert generated["execution_allowed"] is False
    assert generated["parameters"][0]["value"] == 3
    assert generated["parameters"][1]["value"] == 2
    assert all(check["passed"] for check in generated["safety_checks"])

    unsafe = post("Delete all schools and drop the parks table")
    assert unsafe["status"] == "blocked"
    assert unsafe["sql"] is None
    assert unsafe["sql_generated"] is False

    unsupported = post("Find family-friendly concerts this weekend")
    assert unsupported["status"] == "blocked"
    assert unsupported["sql"] is None

    print("Day 7 SQL-generation smoke test PASSED")


if __name__ == "__main__":
    main()
