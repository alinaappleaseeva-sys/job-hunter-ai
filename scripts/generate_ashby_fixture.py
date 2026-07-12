"""Download an Ashby posting API fixture for unit tests.

Ashby is rate-limited — run this script sparingly and commit the result rather
than hitting the live API in CI.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

CLIENT_NAME = "Ashby"
OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "ashby"
    / "ashby_job_board.json"
)


def main() -> None:
    url = (
        f"https://api.ashbyhq.com/posting-api/job-board/{CLIENT_NAME}"
        "?includeCompensation=true"
    )
    response = httpx.get(url, timeout=30.0)
    if response.status_code == 429:
        retry_after = response.headers.get("retry-after", "60")
        wait = int(retry_after) if retry_after.isdigit() else 60
        print(f"Rate limited; waiting {wait}s before retry...")
        time.sleep(wait)
        response = httpx.get(url, timeout=30.0)
    response.raise_for_status()

    payload = response.json()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    job_count = len(payload.get("jobs", [])) if isinstance(payload, dict) else 0
    print(f"Fixture saved to {OUTPUT} ({job_count} jobs)")


if __name__ == "__main__":
    main()