"""Small HTTP smoke test for a running Day 5 API."""

from __future__ import annotations

import argparse
import sys

import httpx


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    checks = [
        ("/health/live", 200),
        ("/health/ready", 200),
        ("/api/v1/snapshot", 200),
        ("/api/v1/neighborhoods?limit=3", 200),
        (
            "/api/v1/schools/near-open-parks"
            "?distance_miles=1&education_level_code=ELEM&limit=3",
            200,
        ),
    ]

    with httpx.Client(base_url=args.base_url, timeout=10.0) as client:
        for path, expected_status in checks:
            response = client.get(path)
            print(f"{response.status_code:>3} {path}")
            if response.status_code != expected_status:
                print(response.text)
                return 1

    print("Day 5 API smoke test PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
