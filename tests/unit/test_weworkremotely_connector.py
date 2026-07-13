"""Tests for We Work Remotely connector (Wave 1)."""

from job_hunter_ai.connectors.weworkremotely import (
    WeWorkRemotelyConnector,
    load_sample_weworkremotely_jobs,
)


def test_weworkremotely_stub():
    samples = load_sample_weworkremotely_jobs()
    # We use real fetch in this test if possible, else just construction
    conn = WeWorkRemotelyConnector()
    # Construction should succeed
    assert conn.source_name == "weworkremotely"


def test_weworkremotely_sample_data():
    samples = load_sample_weworkremotely_jobs()
    assert len(samples) >= 1
    assert "Operations" in samples[0]["title"] or "Program" in samples[0]["title"]