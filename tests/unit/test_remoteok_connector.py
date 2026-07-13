"""Unit tests for Remote OK connector (Phase 8)."""

import json
from pathlib import Path

import pytest

from job_hunter_ai.connectors.remoteok import RemoteOKConnector
from job_hunter_ai.connectors.base import ConnectorEmptyResponseError

FIXTURE = Path("tests/fixtures/remoteok/remoteok_sample.json")

class FakeClient:
    def get(self, url, **kwargs):
        data = json.loads(FIXTURE.read_text())
        class Resp:
            def json(self):
                return data
        return Resp()

def test_remoteok_connector_fetches_and_emits_raw_records():
    conn = RemoteOKConnector(client=FakeClient())
    result = conn.fetch()
    assert len(result.records) >= 1
    rec = result.records[0]
    assert rec.source_name == "remoteok"
    assert rec.source_type == "job_board"
    assert rec.external_id
    assert "Senior" in (rec.payload.get("position") or "")

def test_remoteok_handles_empty():
    class EmptyClient:
        def get(self, url, **kwargs):
            class Resp:
                def json(self): return []
            return Resp()
    conn = RemoteOKConnector(client=EmptyClient())
    with pytest.raises(ConnectorEmptyResponseError):
        conn.fetch()
