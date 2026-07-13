"""Smoke tests for the HTML delivery report generator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from demo.generate_html_report import generate_html_report


def test_generate_html_report_smoke(tmp_path, monkeypatch):
    """Basic smoke test: generator runs and produces a file with real links and profile data."""
    # Mock the pipeline to avoid network and return minimal realistic data
    fake_profile = MagicMock()
    fake_profile.profile_id = "test-profile-123"
    fake_profile.target_role_families = ["Head of Operations"]
    fake_profile.preferred_markets = ["Remote"]
    fake_profile.min_compensation = 120000

    fake_cj = MagicMock()
    fake_cj.canonical_job_id = "weworkremotely-test-123"
    fake_cj.title_normalized = "Head of Something Great"
    fake_cj.company_name = "Example Co"
    fake_cj.url = "https://weworkremotely.com/remote-jobs/head-of-something-great-12345"
    fake_cj.role_family = "Operations"
    fake_cj.seniority = "Senior"
    fake_cj.market = None
    fake_cj.remote_mode = "Remote"
    fake_cj.compensation_min = None

    fake_bd = MagicMock()
    fake_bd.total_score = 0.91
    fake_bd.explanations = []

    fake_rj = MagicMock()
    fake_rj.canonical_job = fake_cj
    fake_rj.score_breakdown = fake_bd

    fake_results = {
        "profile": fake_profile,
        "ranked_jobs": [fake_rj],
        "total_raw": 1,
        "sources": ["weworkremotely"],
    }

    monkeypatch.setattr("demo.generate_html_report.run_full_pipeline", lambda **kw: fake_results)

    out_path = tmp_path / "test_report.html"
    result = generate_html_report(limit_per_source=5, output_path=out_path)

    assert result.exists()
    content = result.read_text(encoding="utf-8")

    # Basic correctness checks (addressing review points)
    assert "Head of Something Great" in content
    assert 'href="https://weworkremotely.com/remote-jobs/head-of-something-great-12345"' in content
    assert "test-profile-123" in content
    assert "<a " in content                     # at least one real <a> link
    assert "&amp;" not in content or "Example" in content  # escaping should not double-escape in this case
    # No raw dangerous tags
    assert "<script>" not in content.lower()
    assert "Alina Aseeva" not in content        # no hard-coded name
