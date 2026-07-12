"""Unit tests for the Lever ATS connector.

Uses respx to mock the public Postings API against a recorded live fixture
(20 real Lever postings from the leverdemo board). No network access required.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from job_hunter_ai.common.models import RawSourceRecord, SourceRunResult
from job_hunter_ai.connectors.base import (
    ConnectorEmptyResponseError,
    ConnectorNetworkError,
    ConnectorRateLimitError,
    ConnectorSchemaError,
)
from job_hunter_ai.connectors.lever import LeverConnector

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "lever"
SITE = "leverdemo"


@pytest.fixture()
def board_payload() -> list[dict]:
    with open(FIXTURE_DIR / "leverdemo.json", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def lever_url() -> str:
    return f"https://api.lever.co/v0/postings/{SITE}?mode=json&limit=100&skip=0"


def test_source_identity() -> None:
    c = LeverConnector(SITE)
    assert c.source_name == "lever:leverdemo"
    assert c.source_type == "ats"
    assert c.url.endswith("/postings/leverdemo?mode=json&limit=100&skip=0")


def test_custom_page_size_reflected_in_url() -> None:
    c = LeverConnector(SITE, page_size=25)
    assert "limit=25" in c.url


def test_empty_site_rejected() -> None:
    with pytest.raises(ValueError):
        LeverConnector("   ")


def test_invalid_page_size_rejected() -> None:
    with pytest.raises(ValueError):
        LeverConnector(SITE, page_size=0)


@respx.mock
def test_fetch_returns_records(board_payload: list[dict], lever_url: str) -> None:
    respx.get(lever_url).mock(return_value=httpx.Response(200, json=board_payload))
    fetch_result = LeverConnector(SITE).fetch()
    records = fetch_result.records

    assert len(records) == len(board_payload)
    first = records[0]
    assert isinstance(first, RawSourceRecord)
    assert first.source_type == "ats"
    assert first.record_type == "job_posting"
    assert first.external_id is not None
    assert first.source_url is not None
    assert first.content_hash is not None
    assert first.metadata["provider"] == "lever"
    assert first.metadata["fetched_via"] == "postings_api"
    assert first.metadata.get("commitment") is not None
    assert first.discovered_at is not None


@respx.mock
def test_location_and_employment_in_metadata(board_payload: list[dict], lever_url: str) -> None:
    respx.get(lever_url).mock(return_value=httpx.Response(200, json=board_payload))
    records = LeverConnector(SITE).fetch().records
    located = [r for r in records if r.metadata.get("location")]
    assert located, "expected at least one posting with a location"
    with_commitment = [r for r in records if r.metadata.get("employment_type")]
    assert with_commitment, "expected commitment/employment_type metadata"


@respx.mock
def test_run_returns_records_and_summary(board_payload: list[dict], lever_url: str) -> None:
    respx.get(lever_url).mock(return_value=httpx.Response(200, json=board_payload))
    fetch_result, summary = LeverConnector(SITE).run()
    records = fetch_result.records

    assert isinstance(summary, SourceRunResult)
    assert summary.success is True
    assert summary.records_emitted == len(records) == len(board_payload)
    assert summary.error_type is None
    assert summary.source_name == "lever:leverdemo"


@respx.mock
def test_empty_board_raises(lever_url: str) -> None:
    respx.get(lever_url).mock(return_value=httpx.Response(200, json=[]))
    with pytest.raises(ConnectorEmptyResponseError):
        LeverConnector(SITE).fetch()


@respx.mock
def test_empty_board_run_reraises(lever_url: str) -> None:
    respx.get(lever_url).mock(return_value=httpx.Response(200, json=[]))
    with pytest.raises(ConnectorEmptyResponseError):
        LeverConnector(SITE).run()


@respx.mock
def test_wrapped_data_shape_supported(lever_url: str, board_payload: list[dict]) -> None:
    respx.get(lever_url).mock(
        return_value=httpx.Response(200, json={"data": board_payload[:3]})
    )
    records = LeverConnector(SITE).fetch().records
    assert len(records) == 3


@respx.mock
def test_data_not_list_raises_schema_error(lever_url: str) -> None:
    respx.get(lever_url).mock(return_value=httpx.Response(200, json={"data": "nope"}))
    with pytest.raises(ConnectorSchemaError):
        LeverConnector(SITE).fetch()


@respx.mock
def test_invalid_top_level_shape_raises_schema_error(lever_url: str) -> None:
    respx.get(lever_url).mock(return_value=httpx.Response(200, json="nope"))
    with pytest.raises(ConnectorSchemaError):
        LeverConnector(SITE).fetch()


@respx.mock
def test_rate_limit_raises(lever_url: str) -> None:
    respx.get(lever_url).mock(
        return_value=httpx.Response(429, headers={"retry-after": "30"})
    )
    with pytest.raises(ConnectorRateLimitError):
        LeverConnector(SITE).fetch()


@respx.mock
def test_network_error_raises(lever_url: str) -> None:
    respx.get(lever_url).mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(ConnectorNetworkError):
        LeverConnector(SITE).fetch()


@respx.mock
def test_non_dict_jobs_skipped(lever_url: str) -> None:
    respx.get(lever_url).mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": "abc",
                    "text": "Real",
                    "hostedUrl": "https://jobs.lever.co/leverdemo/abc",
                    "createdAt": 1502907102690,
                },
                "junk",
                42,
            ],
        )
    )
    records = LeverConnector(SITE).fetch().records
    assert len(records) == 1
    assert records[0].external_id == "abc"


@respx.mock
def test_pagination_drains_multiple_pages() -> None:
    page1_url = f"https://api.lever.co/v0/postings/{SITE}?mode=json&limit=2&skip=0"
    page2_url = f"https://api.lever.co/v0/postings/{SITE}?mode=json&limit=2&skip=2"
    respx.get(page1_url).mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": "1", "text": "One", "hostedUrl": "https://x/1", "createdAt": 1},
                {"id": "2", "text": "Two", "hostedUrl": "https://x/2", "createdAt": 2},
            ],
        )
    )
    respx.get(page2_url).mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": "3", "text": "Three", "hostedUrl": "https://x/3", "createdAt": 3},
            ],
        )
    )

    records = LeverConnector(SITE, page_size=2).fetch().records
    assert len(records) == 3
    assert [r.external_id for r in records] == ["1", "2", "3"]