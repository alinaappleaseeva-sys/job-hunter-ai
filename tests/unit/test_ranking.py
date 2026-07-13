"""Unit + eval tests for ranking v1 (Phase 6).

Uses ranking_topk gold dataset.
Verifies:
- rank_jobs produces ordered output with explanations
- precision@3 meets gate
- explanations are non-empty for scored components
- basic comparison vs chrono baseline
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from job_hunter_ai.common.models import CanonicalJob
from job_hunter_ai.ranking import CandidateProfile, rank_jobs, simple_chrono_baseline

RANKING_GOLD_PATH = Path("evals/datasets/ranking_topk/examples.jsonl")


def _load_ranking_examples() -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    with RANKING_GOLD_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


GOLD_EXAMPLES = _load_ranking_examples()


def _make_canonical_from_gold(j: dict[str, Any]) -> CanonicalJob:
    """Construct minimal CanonicalJob from gold job dict for testing."""
    return CanonicalJob(
        canonical_job_id=j.get("canonical_job_id", "unknown"),
        primary_posting_id=j.get("canonical_job_id", "unknown"),
        company_name=j.get("company_name"),
        company_domain=None,
        title_normalized=j.get("title_normalized") or j.get("title"),
        role_family=j.get("role_family"),
        seniority=j.get("seniority"),
        market=j.get("market"),
        remote_mode=j.get("remote_mode"),
        employment_type=None,
        location_country=j.get("location_country"),
        location_region=None,
        location_city=None,
        compensation_min=j.get("compensation_min"),
        compensation_max=None,
        compensation_currency=j.get("compensation_currency"),
        canonical_posted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),  # fixed for determinism
        first_seen_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        last_seen_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        active_posting_count=1,
        source_count=1,
        ghost_score=None,
        canonical_status="active",
        merge_confidence=None,
        merge_reasons=[],
    )


def _build_profile(p: dict[str, Any]) -> CandidateProfile:
    return CandidateProfile(
        profile_id=p.get("profile_id", "test"),
        target_role_families=p.get("target_role_families", []),
        target_seniorities=p.get("target_seniorities", []),
        target_title_keywords=p.get("target_title_keywords", []),
        remote_preference=p.get("remote_preference"),
        preferred_locations=p.get("preferred_locations", []),
        min_compensation=p.get("min_compensation"),
        compensation_currency=p.get("compensation_currency"),
        preferred_markets=p.get("preferred_markets", []),
    )


def test_ranking_gold_dataset_loads_and_has_minimum_examples():
    assert len(GOLD_EXAMPLES) >= 8
    for ex in GOLD_EXAMPLES:
        assert "example_id" in ex
        assert "profile" in ex and "jobs" in ex
        assert len(ex["jobs"]) >= 3


def test_rank_jobs_produces_explainable_ranking():
    ex = GOLD_EXAMPLES[0]  # first profile with good matches
    profile = _build_profile(ex["profile"])
    jobs = [_make_canonical_from_gold(j) for j in ex["jobs"]]

    ranked = rank_jobs(profile, jobs)

    assert len(ranked) == len(jobs)
    assert all(r.rank is not None for r in ranked)
    # top job should have high score and explanations
    top = ranked[0]
    assert top.score_breakdown.total_score >= 0.5
    assert len(top.score_breakdown.explanations) == 5
    for exp in top.score_breakdown.explanations:
        assert exp.reasons, f"Missing reasons for component {exp.component}"


def test_precision_at_3_meets_phase6_gate():
    """Core gate from ranking_topk.yaml"""
    total_prec = 0.0
    n = 0

    for ex in GOLD_EXAMPLES:
        profile = _build_profile(ex["profile"])
        jobs = [_make_canonical_from_gold(j) for j in ex["jobs"]]
        ranked = rank_jobs(profile, jobs)

        top3 = ranked[:3]
        good = 0
        for r in top3:
            label = next((j.get("relevance_label") for j in ex["jobs"] if j.get("canonical_job_id") == r.canonical_job.canonical_job_id), None)
            if label in ("highly_relevant", "relevant"):
                good += 1

        prec = good / 3.0
        total_prec += prec
        n += 1

    avg_prec = total_prec / max(n, 1)
    assert avg_prec >= 0.60, f"precision@3 = {avg_prec:.2f} < 0.60 gate"


def test_explanation_coverage_gate():
    """At least 80% of top-3 components have non-empty reasons (across gold)"""
    total_explained = 0
    total_components = 0

    for ex in GOLD_EXAMPLES:
        profile = _build_profile(ex["profile"])
        jobs = [_make_canonical_from_gold(j) for j in ex["jobs"]]
        ranked = rank_jobs(profile, jobs)

        for r in ranked[:3]:
            for exp in r.score_breakdown.explanations:
                total_components += 1
                if exp.reasons:
                    total_explained += 1

    coverage = total_explained / max(total_components, 1)
    assert coverage >= 0.80, f"explanation coverage {coverage:.2f} < 0.80"


def test_ranker_beats_or_matches_simple_chrono_baseline():
    """Weak check: our ranker should not be worse than pure chrono on this synthetic set."""
    for ex in GOLD_EXAMPLES[:4]:  # sample a few
        profile = _build_profile(ex["profile"])
        jobs = [_make_canonical_from_gold(j) for j in ex["jobs"]]

        ranked = rank_jobs(profile, jobs)
        baseline = simple_chrono_baseline(jobs)

        # Count how many highly/relevant are in top 3
        def top3_good(items):
            good = 0
            for item in items[:3]:
                if hasattr(item, "canonical_job"):
                    jid = item.canonical_job.canonical_job_id
                else:
                    jid = getattr(item, "canonical_job_id", None) or getattr(item, "canonical_job_id", "unknown")
                label = next((jj.get("relevance_label") for jj in ex["jobs"] if jj.get("canonical_job_id") == jid), None)
                if label in ("highly_relevant", "relevant"):
                    good += 1
            return good

        our_good = top3_good(ranked)
        base_good = top3_good(baseline)

        # Our ranker should be at least as good as baseline on this data
        assert our_good >= base_good, f"ranker {our_good} < baseline {base_good} on {ex['example_id']}"


def test_ranking_suite_yaml_exists():
    suite_path = Path("evals/suites/ranking_topk.yaml")
    assert suite_path.exists()
    content = suite_path.read_text()
    assert "precision_at_3" in content


# Phase 2 additions: tests for CoS / Head of Ops boosts + new gold dataset

import json
from pathlib import Path

PHASE2_GOLD_PATH = Path("evals/datasets/head_ops_cos_gold/examples.jsonl")

def _load_phase2_gold():
    if not PHASE2_GOLD_PATH.exists():
        return []
    examples = []
    with PHASE2_GOLD_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples

PHASE2_GOLD = _load_phase2_gold()

def test_phase2_cos_head_ops_boosts():
    """Phase 2: high-priority titles (chief of staff, head of operations) should get strong role_fit."""
    from job_hunter_ai.ranking.ranking import _score_role_fit, DEFAULT_WEIGHTS
    from job_hunter_ai.common.models import CandidateProfile, CanonicalJob
    from datetime import datetime, timezone

    profile = CandidateProfile(
        profile_id="test",
        target_role_families=["chief_of_staff", "operations"],
        target_seniorities=["head"],
        target_title_keywords=["chief of staff", "head of operations", "ops"],
        remote_preference="remote",
        min_compensation=120000,
    )

    # Simulate a job with exact high priority title
    job_cos = CanonicalJob(
        canonical_job_id="test-cos",
        primary_posting_id="test-cos",
        company_name="DAO Co",
        company_domain=None,
        title_normalized="chief of staff",
        role_family="chief_of_staff",
        seniority="head",
        market="web3",
        remote_mode="remote",
        employment_type=None,
        location_country="Remote",
        location_region=None,
        location_city=None,
        compensation_min=140000,
        compensation_max=None,
        compensation_currency="USD",
        canonical_posted_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        first_seen_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        last_seen_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        active_posting_count=1,
        source_count=1,
        ghost_score=None,
        canonical_status="active",
        merge_confidence=None,
        merge_reasons=[],
    )

    score, reasons = _score_role_fit(profile, job_cos)
    assert score >= 0.9, f"Expected high score for CoS title, got {score}"
    assert any("high-priority" in r or "chief of staff" in " ".join(reasons).lower() for r in reasons), "Expected high-priority boost reason"

def test_phase2_head_ops_cos_gold():
    """Phase 2: basic smoke on new CoS/Head Ops gold dataset."""
    if not PHASE2_GOLD:
        return  # skip if not present
    for ex in PHASE2_GOLD[:2]:
        profile = _build_profile(ex["profile"])
        jobs = [_make_canonical_from_gold(j) for j in ex["jobs"]]
        ranked = rank_jobs(profile, jobs)
        # At least one highly_relevant should be in top 2 for these examples
        top_ids = [rj.canonical_job.canonical_job_id for rj in ranked[:2]]
        highly = [j["canonical_job_id"] for j in ex["jobs"] if j.get("relevance_label") == "highly_relevant"]
        overlap = set(top_ids) & set(highly)
        assert len(overlap) >= 1, f"Expected highly relevant CoS/Head Ops in top for {ex['example_id']}"
