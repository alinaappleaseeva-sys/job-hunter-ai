"""Unit tests for the Greenhouse ATS connector.

Uses respx to mock the public Job Board API against a recorded live fixture
(20 real Greenhouse postings from the Stripe board). No network access is
required to run these tests.
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
from job_hunter_ai.connectors.greenhouse import GreenhouseConnector

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "greenhouse"


@pytest.fixture()
def board_payload() -> dict:
    with open(FIXTURE_DIR / "greenhouse_job_board.json", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def gh_url() -> str:
    return "https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true"


def test_source_identity() -> None:
    c = GreenhouseConnector("stripe")
    assert c.source_name == "greenhouse:stripe"
    assert c.source_type == "ats"
    assert c.url.endswith("/boards/stripe/jobs?content=true")


def test_url_without_content() -> None:
    c = GreenhouseConnector("stripe", include_content=False)
    assert c.url == "https://boards-api.greenhouse.io/v1/boards/stripe/jobs"


def test_empty_board_token_rejected() -> None:
    with pytest.raises(ValueError):
        GreenhouseConnector("   ")


@respx.mock
def test_fetch_returns_records(board_payload: dict, gh_url: str) -> None:
    respx.get(gh_url).mock(return_value=httpx.Response(200, json=board_payload))
    fetch_result = GreenhouseConnector("stripe").fetch()
    records = fetch_result.records

    assert len(records) == len(board_payload["jobs"])
    first = records[0]
    assert isinstance(first, RawSourceRecord)
    assert first.source_type == "ats"
    assert first.record_type == "job_posting"
    assert first.external_id is not None
    assert first.source_url is not None
    assert first.content_hash is not None
    assert first.metadata["provider"] == "greenhouse"
    assert first.metadata["fetched_via"] == "job_board_api"
    assert "company_name" in first.metadata
    assert first.discovered_at is not None


@respx.mock
def test_location_flattened_into_metadata(board_payload: dict, gh_url: str) -> None:
    respx.get(gh_url).mock(return_value=httpx.Response(200, json=board_payload))
    records = GreenhouseConnector("stripe").fetch().records
    located = [r for r in records if r.metadata.get("location_name")]
    assert located, "expected at least one posting with a location name"


@respx.mock
def test_run_returns_records_and_summary(board_payload: dict, gh_url: str) -> None:
    respx.get(gh_url).mock(return_value=httpx.Response(200, json=board_payload))
    fetch_result, summary = GreenhouseConnector("stripe").run()
    records = fetch_result.records

    assert isinstance(summary, SourceRunResult)
    assert summary.success is True
    assert summary.records_emitted == len(records) == len(board_payload["jobs"])
    assert summary.error_type is None
    assert summary.source_name == "greenhouse:stripe"


@respx.mock
def test_empty_board_raises(gh_url: str) -> None:
    respx.get(gh_url).mock(
        return_value=httpx.Response(200, json={"jobs": [], "meta": {"total": 0}})
    )
    with pytest.raises(ConnectorEmptyResponseError):
        GreenhouseConnector("stripe").fetch()


@respx.mock
def test_empty_board_run_reraises(gh_url: str) -> None:
    respx.get(gh_url).mock(
        return_value=httpx.Response(200, json={"jobs": [], "meta": {"total": 0}})
    )
    with pytest.raises(ConnectorEmptyResponseError):
        GreenhouseConnector("stripe").run()


@respx.mock
def test_missing_jobs_key_raises_schema_error(gh_url: str) -> None:
    respx.get(gh_url).mock(return_value=httpx.Response(200, json={"meta": {"total": 0}}))
    with pytest.raises(ConnectorSchemaError):
        GreenhouseConnector("stripe").fetch()


@respx.mock
def test_jobs_not_a_list_raises_schema_error(gh_url: str) -> None:
    respx.get(gh_url).mock(return_value=httpx.Response(200, json={"jobs": "nope"}))
    with pytest.raises(ConnectorSchemaError):
        GreenhouseConnector("stripe").fetch()


@respx.mock
def test_rate_limit_raises(gh_url: str) -> None:
    respx.get(gh_url).mock(
        return_value=httpx.Response(429, headers={"retry-after": "30"})
    )
    with pytest.raises(ConnectorRateLimitError):
        GreenhouseConnector("stripe").fetch()


@respx.mock
def test_network_error_raises(gh_url: str) -> None:
    respx.get(gh_url).mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(ConnectorNetworkError):
        GreenhouseConnector("stripe").fetch()


@respx.mock
def test_non_dict_jobs_skipped(gh_url: str) -> None:
    respx.get(gh_url).mock(
        return_value=httpx.Response(
            200,
            json={
                "jobs": [{"id": 1, "title": "Real", "absolute_url": "http://x"}, "junk", 42],
                "meta": {"total": 3},
            },
        )
    )
    records = GreenhouseConnector("stripe").fetch().records
    assert len(records) == 1
    assert records[0].external_id == "1"