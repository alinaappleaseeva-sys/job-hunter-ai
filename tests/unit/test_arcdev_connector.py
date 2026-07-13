"""Tests for Arc.dev connector (Wave 1)."""

from job_hunter_ai.connectors.arcdev import ArcDevConnector, load_sample_arcdev_jobs


def test_arcdev_basic():
    conn = ArcDevConnector()
    res = conn.fetch(limit=3)
    assert len(res.records) >= 1


def test_arcdev_samples():
    samples = load_sample_arcdev_jobs()
    assert any("Operations" in s["title"] or "Program" in s["title"] for s in samples)