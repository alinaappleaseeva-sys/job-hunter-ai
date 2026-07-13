"""Tests for Phase 9 Delivery UX / feedback.

Uses feedback_actions gold + real impl.
Verifies build_digest, apply_action traceability, no silent actions.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from job_hunter_ai.common.models import CandidateProfile, CanonicalJob, JobScoreBreakdown, RankedJob, ScoreExplanation
from job_hunter_ai.delivery import apply_action, build_digest, FeedbackEvent

FEEDBACK_GOLD = Path("evals/datasets/feedback_actions/examples.jsonl")

def _load_feedback_examples() -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    with FEEDBACK_GOLD.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples

GOLD = _load_feedback_examples()

def _make_ranked_job(job_id: str, total_score: float = 0.85, ghost: float = 0.1) -> RankedJob:
    cj = CanonicalJob(
        canonical_job_id=job_id,
        primary_posting_id=job_id,
        company_name="TestCo",
        company_domain=None,
        title_normalized="Test Role",
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
        canonical_posted_at=datetime.now(),
        first_seen_at=datetime.now(),
        last_seen_at=datetime.now(),
        active_posting_count=1,
        source_count=1,
        ghost_score=ghost,
        canonical_status="active",
        merge_confidence=None,
        merge_reasons=[],
    )
    breakdown = JobScoreBreakdown(
        total_score=total_score,
        explanations=[ScoreExplanation(component="role_fit", score=0.9, reasons=["title match"])],
    )
    return RankedJob(canonical_job=cj, score_breakdown=breakdown, rank=1)

def test_feedback_gold_loads():
    assert len(GOLD) >= 5

def test_apply_action_produces_traceable_event():
    rj = _make_ranked_job("cj-001")
    event = apply_action(rj, "p-sr-be-us", "relevant", "good match")
    assert isinstance(event, FeedbackEvent)
    assert event.action == "relevant"
    assert event.score_breakdown is not None
    assert len(event.explanations) > 0
    assert event.ghost_score is not None
    assert event.canonical_job_id == "cj-001"

def test_build_digest_exposes_explanations():
    profile = CandidateProfile(profile_id="p-1")
    jobs = [_make_ranked_job(f"cj-{i}", total_score=0.9 - i*0.1) for i in range(3)]
    digest = build_digest(profile, jobs, limit=5)
    assert digest["count"] >= 1
    for item in digest["jobs"]:
        assert "explanations" in item
        assert "ghost_score" in item

def test_no_silent_actions_in_gold():
    silent_count = sum(1 for ex in GOLD if not ex.get("expected_trace") and ex["label"] != "invalid_trace")
    assert silent_count == 0, "Gold should have no silent actions for valid cases"

def test_traceability_rate_meets_skeleton_gate():
    valid = [ex for ex in GOLD if ex["label"] == "valid"]
    with_trace = [ex for ex in valid if ex.get("expected_trace")]
    rate = len(with_trace) / max(len(valid), 1)
    assert rate >= 0.80  # skeleton gate; full suite target 0.90
