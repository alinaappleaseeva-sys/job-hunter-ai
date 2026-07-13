"""Tests for Workable connector (Wave 1)."""

from job_hunter_ai.connectors.workable import WorkableConnector, load_sample_workable_jobs


def test_workable_construction():
    conn = WorkableConnector(subdomain="example")
    assert "workable" in conn.source_name
    assert conn.subdomain == "example"


def test_workable_samples():
    samples = load_sample_workable_jobs()
    assert len(samples) >= 1
    assert any("Operations" in s.get("title", "") or "Program" in s.get("title", "") for s in samples)
