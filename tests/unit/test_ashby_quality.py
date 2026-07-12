"""Ashby payload field-presence smoke test.

Quality scoring runs on normalized postings (see test_connectors_quality).
This test confirms Ashby emits raw records with the fields downstream
normalization will need.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from job_hunter_ai.connectors.ashby import AshbyConnector

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "ashby"
ASHBY_URL = "https://api.ashbyhq.com/posting-api/job-board/Ashby?includeCompensation=true"


@respx.mock
def test_ashby_records_carry_expected_payload_fields() -> None:
    with open(FIXTURE_DIR / "ashby_job_board.json", encoding="utf-8") as fh:
        board_payload = json.load(fh)

    respx.get(ASHBY_URL).mock(return_value=httpx.Response(200, json=board_payload))
    records = AshbyConnector("Ashby").fetch().records

    assert records
    first = records[0]
    assert first.payload.get("title")
    assert first.payload.get("descriptionPlain") or first.payload.get("descriptionHtml")
    assert first.metadata.get("employment_type") is not None
    assert first.metadata.get("location_name") is not None
    assert first.metadata.get("remote_mode") is not None
    assert first.metadata.get("company_name") == "Ashby"