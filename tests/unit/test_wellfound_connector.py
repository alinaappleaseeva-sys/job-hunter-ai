"""Tests for Wellfound connector stub (Phase 8 remaining)."""

import json
from pathlib import Path

from job_hunter_ai.connectors.wellfound import WellfoundConnector, load_sample_wellfound_jobs

FIXTURE = Path("tests/fixtures/wellfound/wellfound_sample.json")

def test_wellfound_stub_from_sample():
    jobs = load_sample_wellfound_jobs()
    conn = WellfoundConnector(jobs=jobs)
    result = conn.fetch()
    assert len(result.records) >= 1
    rec = result.records[0]
    assert rec.source_name == "wellfound"
    assert rec.source_type == "job_board"
    assert "Senior Software" in rec.payload.get("title", "")

def test_wellfound_loads_fixture():
    data = json.loads(FIXTURE.read_text())
    assert len(data) >= 1
    assert "title" in data[0] or "position" in data[0]