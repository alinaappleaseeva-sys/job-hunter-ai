"""Tests for real Wellfound connector (Wave 1)."""

from job_hunter_ai.connectors.wellfound import WellfoundConnector, load_sample_wellfound_jobs


def test_wellfound_construction():
    conn = WellfoundConnector()
    assert conn.source_name == "wellfound"


def test_wellfound_samples_still_work():
    samples = load_sample_wellfound_jobs()
    assert len(samples) >= 2
    assert any("Operations" in j.get("title", "") for j in samples)


def test_wellfound_fetch_runs():
    """Smoke: the real fetch should not crash (may return 0 if page structure changed)."""
    conn = WellfoundConnector()
    result = conn.fetch(limit=5)
    # We don't assert count because scraping is brittle, but it must return a FetchResult
    assert hasattr(result, "records")
    assert isinstance(result.records, list)
