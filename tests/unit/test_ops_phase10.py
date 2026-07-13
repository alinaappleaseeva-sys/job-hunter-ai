"""Quick tests for remaining Phase 10 ops skeletons."""

from job_hunter_ai.ops.triage import triage_degraded_sources
from job_hunter_ai.ops.regression_review import generate_regression_review_summary
from job_hunter_ai.ops.rollout import can_rollout_source
from job_hunter_ai.ops.source_health import SourceHealthSummary


def test_triage():
    summaries = {
        "bad-src": SourceHealthSummary(source_name="bad-src", status="degraded", total_fetches=10, successful_fetches=4, avg_parse_quality=0.5, stale_ratio=0.4),
    }
    actions = triage_degraded_sources(summaries)
    assert len(actions) == 1
    assert actions[0]["recommendation"] == "pause"


def test_regression_review():
    report = generate_regression_review_summary(
        {"precision_at_3": 0.72},
        {"precision_at_3": 0.65},
        "tightened role fit",
    )
    assert report["recommendation"] in ("block_or_mitigate", "add_explanation_and_rerun")


def test_rollout():
    ok, reasons = can_rollout_source("web3-ops", {
        "eval_coverage": 0.9,
        "noise_rate": 0.2,
        "precision_at_3": 0.62,
        "health_status": "healthy",
    })
    assert ok is True
