"""Lever payload field-presence smoke test."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from job_hunter_ai.connectors.lever import LeverConnector

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "lever"
LEVER_URL = "https://api.lever.co/v0/postings/leverdemo?mode=json&limit=100&skip=0"


@respx.mock
def test_lever_records_carry_expected_payload_fields() -> None:
    with open(FIXTURE_DIR / "leverdemo.json", encoding="utf-8") as fh:
        board_payload = json.load(fh)

    respx.get(LEVER_URL).mock(return_value=httpx.Response(200, json=board_payload))
    records = LeverConnector("leverdemo").fetch().records

    assert records
    first = records[0]
    assert first.payload.get("text")
    assert first.payload.get("description") or first.payload.get("descriptionPlain")
    assert first.metadata.get("location") is not None
    assert first.metadata.get("employment_type") is not None
    assert first.metadata.get("remote_mode") is not None or first.payload.get("workplaceType")