"""Unit tests for the Ashby ATS connector.

Uses respx to mock the public posting API against a recorded live fixture
(64 real Ashby postings). No network access is required to run these tests.
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
from job_hunter_ai.connectors.ashby import AshbyConnector

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "ashby"
CLIENT = "Ashby"


@pytest.fixture()
def board_payload() -> dict:
    with open(FIXTURE_DIR / "ashby_job_board.json", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def ashby_url() -> str:
    return f"https://api.ashbyhq.com/posting-api/job-board/{CLIENT}?includeCompensation=true"


def test_source_identity() -> None:
    c = AshbyConnector(CLIENT)
    assert c.source_name == "ashby:Ashby"
    assert c.source_type == "ats"
    assert c.url.endswith("/job-board/Ashby?includeCompensation=true")


def test_url_without_compensation() -> None:
    c = AshbyConnector(CLIENT, include_compensation=False)
    assert c.url == "https://api.ashbyhq.com/posting-api/job-board/Ashby"


def test_empty_client_name_rejected() -> None:
    with pytest.raises(ValueError):
        AshbyConnector("   ")


def test_invalid_timeout_rejected() -> None:
    with pytest.raises(ValueError):
        AshbyConnector(CLIENT, request_timeout=0)


@respx.mock
def test_fetch_returns_records(board_payload: dict, ashby_url: str) -> None:
    respx.get(ashby_url).mock(return_value=httpx.Response(200, json=board_payload))
    fetch_result = AshbyConnector(CLIENT).fetch()
    records = fetch_result.records

    assert len(records) == len(board_payload["jobs"])
    first = records[0]
    assert isinstance(first, RawSourceRecord)
    assert first.source_type == "ats"
    assert first.record_type == "job_posting"
    assert first.external_id is not None
    assert first.source_url is not None
    assert first.content_hash is not None
    assert first.metadata["provider"] == "ashby"
    assert first.metadata["fetched_via"] == "posting_api"
    assert first.metadata.get("employment_type") is not None
    assert first.metadata.get("remote_mode") is not None
    assert first.discovered_at is not None


@respx.mock
def test_run_metadata_includes_rate_limit_tier(board_payload: dict, ashby_url: str) -> None:
    respx.get(ashby_url).mock(return_value=httpx.Response(200, json=board_payload))
    fetch_result, _ = AshbyConnector(CLIENT).run()
    assert fetch_result.run_metadata["rate_limit_tier"] == "tier_2"
    assert fetch_result.run_metadata["raw_job_count"] == len(board_payload["jobs"])


@respx.mock
def test_location_in_metadata(board_payload: dict, ashby_url: str) -> None:
    respx.get(ashby_url).mock(return_value=httpx.Response(200, json=board_payload))
    records = AshbyConnector(CLIENT).fetch().records
    located = [r for r in records if r.metadata.get("location_name")]
    assert located, "expected at least one posting with a location"


@respx.mock
def test_run_returns_records_and_summary(board_payload: dict, ashby_url: str) -> None:
    respx.get(ashby_url).mock(return_value=httpx.Response(200, json=board_payload))
    fetch_result, summary = AshbyConnector(CLIENT).run()
    records = fetch_result.records

    assert isinstance(summary, SourceRunResult)
    assert summary.success is True
    assert summary.records_emitted == len(records) == len(board_payload["jobs"])
    assert summary.error_type is None
    assert summary.source_name == "ashby:Ashby"


@respx.mock
def test_fetch_limit_caps_records(board_payload: dict, ashby_url: str) -> None:
    respx.get(ashby_url).mock(return_value=httpx.Response(200, json=board_payload))
    records = AshbyConnector(CLIENT).fetch(limit=5).records
    assert len(records) == 5


@respx.mock
def test_empty_board_raises(ashby_url: str) -> None:
    respx.get(ashby_url).mock(
        return_value=httpx.Response(200, json={"jobs": [], "apiVersion": "1"})
    )
    with pytest.raises(ConnectorEmptyResponseError):
        AshbyConnector(CLIENT).fetch()


@respx.mock
def test_empty_board_run_reraises(ashby_url: str) -> None:
    respx.get(ashby_url).mock(
        return_value=httpx.Response(200, json={"jobs": [], "apiVersion": "1"})
    )
    with pytest.raises(ConnectorEmptyResponseError):
        AshbyConnector(CLIENT).run()


@respx.mock
def test_missing_jobs_key_raises_schema_error(ashby_url: str) -> None:
    respx.get(ashby_url).mock(return_value=httpx.Response(200, json={"apiVersion": "1"}))
    with pytest.raises(ConnectorSchemaError):
        AshbyConnector(CLIENT).fetch()


@respx.mock
def test_jobs_not_a_list_raises_schema_error(ashby_url: str) -> None:
    respx.get(ashby_url).mock(return_value=httpx.Response(200, json={"jobs": "nope"}))
    with pytest.raises(ConnectorSchemaError):
        AshbyConnector(CLIENT).fetch()


@respx.mock
def test_rate_limit_raises(ashby_url: str) -> None:
    respx.get(ashby_url).mock(
        return_value=httpx.Response(429, headers={"retry-after": "60"})
    )
    with pytest.raises(ConnectorRateLimitError, match="retry-after=60"):
        AshbyConnector(CLIENT).fetch()


@respx.mock
def test_network_error_raises(ashby_url: str) -> None:
    respx.get(ashby_url).mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(ConnectorNetworkError):
        AshbyConnector(CLIENT).fetch()


@respx.mock
def test_non_dict_jobs_skipped(ashby_url: str) -> None:
    respx.get(ashby_url).mock(
        return_value=httpx.Response(
            200,
            json={
                "jobs": [{"id": "1", "title": "Real"}, "garbage", 42],
                "apiVersion": "1",
            },
        )
    )
    records = AshbyConnector(CLIENT).fetch().records
    assert len(records) == 1
    assert records[0].external_id == "1"