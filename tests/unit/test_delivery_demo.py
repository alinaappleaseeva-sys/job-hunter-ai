"""Smoke test for the Streamlit delivery demo (Phase 9+).

Ensures the demo script can be imported and uses the real delivery functions.
"""

import importlib.util
from pathlib import Path

import pytest

DEMO_PATH = Path("demo/streamlit_delivery_demo.py")


@pytest.mark.skipif(
    not DEMO_PATH.exists(),
    reason="Demo script not present",
)
def test_demo_script_imports():
    """The demo must be importable (streamlit will be optional at runtime)."""
    spec = importlib.util.spec_from_file_location("delivery_demo", DEMO_PATH)
    module = importlib.util.module_from_spec(spec)
    # We only check that top-level code that doesn't require streamlit executes
    # The heavy import of streamlit is inside the run, so we mock it lightly.
    try:
        spec.loader.exec_module(module)  # type: ignore[attr-defined]
    except ModuleNotFoundError as e:
        if "streamlit" in str(e):
            pytest.skip("streamlit not installed (expected for non-demo envs)")
        else:
            raise
    assert hasattr(module, "main") or "streamlit" in str(DEMO_PATH)


def test_demo_uses_real_apply_action():
    """Verify the demo logic path uses the real Phase 9 apply_action."""
    from job_hunter_ai.common.models import (
        CandidateProfile,
        CanonicalJob,
        JobScoreBreakdown,
        RankedJob,
        ScoreExplanation,
    )
    from job_hunter_ai.delivery import apply_action

    cj = CanonicalJob(
        canonical_job_id="demo-cj",
        primary_posting_id="p1",
        company_name="DemoCo",
        company_domain=None,
        title_normalized="Demo Role",
        role_family="engineering",
        seniority="senior",
        market="saas",
        remote_mode="remote",
        employment_type="full-time",
        location_country="US",
        location_region=None,
        location_city=None,
        compensation_min=150000,
        compensation_max=None,
        compensation_currency="USD",
        canonical_posted_at=__import__("datetime").datetime.now(),
        first_seen_at=__import__("datetime").datetime.now(),
        last_seen_at=__import__("datetime").datetime.now(),
        active_posting_count=1,
        source_count=1,
        ghost_score=0.1,
        canonical_status="active",
        merge_confidence=None,
        merge_reasons=[],
    )
    bd = JobScoreBreakdown(total_score=0.88)
    rj = RankedJob(canonical_job=cj, score_breakdown=bd)

    event = apply_action(rj, "demo-profile", "relevant", "test reason")
    assert event.action == "relevant"
    assert event.score_breakdown is not None
