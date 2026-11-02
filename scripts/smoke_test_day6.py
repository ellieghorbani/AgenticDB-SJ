#!/usr/bin/env python3
"""Live HTTP smoke test for Day 6 schema and planning endpoints."""

from __future__ import annotations

import os

import httpx


BASE_URL = os.getenv("AGENTICDB_API_URL", "http://127.0.0.1:8000")


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=15.0) as client:
        response = client.get("/api/v1/copilot/schema")
        response.raise_for_status()
        catalog = response.json()
        assert catalog["relation_count"] == 6
        print(f"{response.status_code} /api/v1/copilot/schema")

        response = client.post(
            "/api/v1/copilot/schema/retrieve",
            json={
                "question": "Which elementary schools are within one mile of an open park?",
                "top_k": 6,
            },
        )
        response.raise_for_status()
        context = response.json()
        names = {
            item["relation"]["qualified_name"]
            for item in context["relations"]
        }
        assert "core.parks" in names
        print(f"{response.status_code} /api/v1/copilot/schema/retrieve")

        response = client.post(
            "/api/v1/copilot/plan",
            json={
                "question": (
                    "Which neighborhoods contain at least three active schools "
                    "and two open park features?"
                )
            },
        )
        response.raise_for_status()
        plan = response.json()["plan"]
        assert plan["intent"] == "neighborhoods_with_minimum_schools_and_parks"
        assert plan["query_type"] == "hybrid"
        assert plan["execution_allowed"] is False
        assert plan["sql_generated"] is False
        print(f"{response.status_code} /api/v1/copilot/plan")

        response = client.post(
            "/api/v1/copilot/plan",
            json={"question": "Delete all schools"},
        )
        response.raise_for_status()
        unsafe_plan = response.json()["plan"]
        assert unsafe_plan["intent"] == "unsafe_request"
        assert unsafe_plan["query_type"] == "unsupported"
        print(f"{response.status_code} /api/v1/copilot/plan (unsafe request blocked)")

    print("Day 6 schema/planner smoke test PASSED")


if __name__ == "__main__":
    main()
