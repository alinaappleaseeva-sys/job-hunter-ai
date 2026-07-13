"""Tests for Wellfound connector (Wave 1 real + backward sample support)."""

from job_hunter_ai.connectors.wellfound import WellfoundConnector, load_sample_wellfound_jobs


def test_wellfound_from_samples():
    """The connector should always be able to produce records via samples/fallback."""
    conn = WellfoundConnector()
    result = conn.fetch(limit=2)
    assert len(result.records) >= 1
    rec = result.records[0]
    assert rec.source_name == "wellfound"
    assert rec.source_type == "job_board"


def test_wellfound_samples_have_ops_content():
    jobs = load_sample_wellfound_jobs()
    titles = " ".join(j.get("title", "") for j in jobs)
    assert "Operations" in titles or "Program" in titles