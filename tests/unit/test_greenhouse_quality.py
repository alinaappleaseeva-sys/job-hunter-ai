"""Greenhouse payload field-presence smoke test.

Quality scoring now runs on normalized postings (see test_connectors_quality).
This test confirms the Greenhouse connector emits raw records with the payload
fields downstream normalization will need.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from job_hunter_ai.connectors.greenhouse import GreenhouseConnector

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "greenhouse"
GH_URL = "https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true"


@respx.mock
def test_greenhouse_records_carry_expected_payload_fields() -> None:
    with open(FIXTURE_DIR / "greenhouse_job_board.json", encoding="utf-8") as fh:
        board_payload = json.load(fh)

    respx.get(GH_URL).mock(return_value=httpx.Response(200, json=board_payload))
    records = GreenhouseConnector("stripe").fetch().records

    assert records
    first = records[0]
    assert first.payload.get("title")
    assert first.payload.get("content") or first.payload.get("absolute_url")
    assert first.metadata.get("company_name") is not None
    assert first.metadata.get("location_name") is not None or first.payload.get("location")
    assert first.metadata.get("employment_type") is None