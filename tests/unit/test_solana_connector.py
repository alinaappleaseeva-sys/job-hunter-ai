"""Tests for Solana Jobs connector stub (Phase 8 remaining)."""

import json
from pathlib import Path

from job_hunter_ai.connectors.solana import SolanaJobsConnector, load_sample_solana_jobs

FIXTURE = Path("tests/fixtures/solana/solana_sample.json")

def test_solana_stub_from_sample():
    jobs = load_sample_solana_jobs()
    conn = SolanaJobsConnector(jobs=jobs)
    result = conn.fetch()
    assert len(result.records) >= 1
    rec = result.records[0]
    assert rec.source_name == "solana"
    assert rec.source_type == "job_board"
    assert "Trading Growth" in rec.payload.get("title", "")

def test_solana_loads_fixture():
    data = json.loads(FIXTURE.read_text())
    assert len(data) >= 1
    assert "title" in data[0]