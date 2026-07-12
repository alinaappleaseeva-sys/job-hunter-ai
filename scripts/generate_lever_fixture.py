"""Download a Lever Postings API fixture for unit tests."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

SITE = "leverdemo"
LIMIT = 20
OUTPUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "lever" / "leverdemo.json"


def main() -> None:
    url = f"https://api.lever.co/v0/postings/{SITE}?mode=json&limit={LIMIT}"
    response = httpx.get(url, timeout=30.0)
    response.raise_for_status()
    payload = response.json()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    count = len(payload) if isinstance(payload, list) else len(payload.get("data", []))
    print(f"Fixture saved to {OUTPUT} ({count} jobs)")


if __name__ == "__main__":
    main()