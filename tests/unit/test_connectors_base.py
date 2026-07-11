from __future__ import annotations

from datetime import datetime

import pytest

from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.connectors.base import Connector
from job_hunter_ai.connectors.base import ConnectorNetworkError
from job_hunter_ai.connectors.base import FetchResult
from job_hunter_ai.connectors.base import make_content_hash


class DummyConnector(Connector):
    def __init__(self) -> None:
        super().__init__(source_name="dummy", source_type="ats")

    def fetch(
        self,
        *,
        cursor_value: str | None = None,
        limit: int | None = None,
    ) -> FetchResult:
        return FetchResult(
            records=[
                RawSourceRecord(
                    source_name=self.source_name,
                    source_type=self.source_type,
                    record_type="job_posting",
                    external_id="123",
                    source_url="https://example.com/jobs/123",
                    fetched_at=datetime.now(),
                    discovered_at=None,
                    payload={"title": "Product Manager"},
                    content_hash="abc",
                    cursor_value=cursor_value,
                    metadata={"limit": limit},
                )
            ],
            cursor_after="next-cursor",
            run_metadata={"mode": "test"},
        )


class FailingConnector(Connector):
    def __init__(self) -> None:
        super().__init__(source_name="failing", source_type="job_board")

    def fetch(
        self,
        *,
        cursor_value: str | None = None,
        limit: int | None = None,
    ) -> FetchResult:
        raise ConnectorNetworkError("network down")


def test_make_content_hash_returns_none_for_missing_or_empty_values() -> None:
    assert make_content_hash(None) is None
    assert make_content_hash("") is None
    assert make_content_hash(b"") is None


def test_make_content_hash_is_stable_for_text_input() -> None:
    first = make_content_hash("hello world")
    second = make_content_hash("hello world")

    assert first is not None
    assert first == second


def test_connector_run_returns_records_and_run_summary() -> None:
    connector = DummyConnector()

    fetch_result, run_result = connector.run(cursor_value="cursor-1", limit=25)

    assert len(fetch_result.records) == 1
    assert run_result.success is True
    assert run_result.records_fetched == 1
    assert run_result.records_emitted == 1
    assert run_result.records_persisted == 0
    assert run_result.cursor_before == "cursor-1"
    assert run_result.cursor_after == "next-cursor"
    assert run_result.run_metadata == {"mode": "test"}


def test_connector_run_reraises_connector_errors() -> None:
    connector = FailingConnector()

    with pytest.raises(ConnectorNetworkError, match="network down"):
        connector.run()

