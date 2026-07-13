"""Tests for ghosting v1 (Phase 7).

Uses ghosting_precision gold dataset.
Verifies gates and explainability.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from job_hunter_ai.common.models import CanonicalJob
from job_hunter_ai.ghosting import compute_ghost_score, decide_visibility

GHOST_GOLD_PATH = Path("evals/datasets/ghosting_precision/examples.jsonl")


def _load_ghost_examples() -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    with GHOST_GOLD_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


GOLD_EXAMPLES = _load_ghost_examples()


def _make_canonical(ex: dict[str, Any]) -> CanonicalJob:
    """Create a minimal CanonicalJob for ghost scoring tests.

    Uses signals to simulate posted_at age and source hints.
    """
    label = ex["ghost_label"]
    signals = ex["signals"]

    # Simulate age
    if "old_posting_age" in signals or label in ("stale", "suspicious_evergreen"):
        posted = datetime.now(timezone.utc) - timedelta(days=120)
    else:
        posted = datetime.now(timezone.utc) - timedelta(days=5)

    # Simulate source count for repost
    source_count = 3 if "repost_pattern" in signals or "secondary_source_only" in signals else 1

    return CanonicalJob(
        canonical_job_id=ex["example_id"],
        primary_posting_id=ex["example_id"],
        company_name="ExampleCo",
        company_domain=None,
        title_normalized="example role",
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
        canonical_posted_at=posted,
        first_seen_at=posted,
        last_seen_at=posted,
        active_posting_count=1,
        source_count=source_count,
        ghost_score=None,
        canonical_status="active",
        merge_confidence=None,
        merge_reasons=[],
    )


def test_ghosting_gold_loads():
    assert len(GOLD_EXAMPLES) >= 8


def test_compute_ghost_score_produces_reasons_and_score_range():
    for ex in GOLD_EXAMPLES[:5]:
        job = _make_canonical(ex)
        score, reasons = compute_ghost_score(job)
        assert 0.0 <= score <= 1.0
        assert isinstance(reasons, list)
        assert len(reasons) >= 1


def test_decide_visibility_policy():
    # low
    action, _ = decide_visibility(0.1, ["no_ghost_signals"])
    assert action == "show"

    # downrank
    action, _ = decide_visibility(0.45, ["secondary_source_only"])
    assert action == "downrank"

    # hide
    action, _ = decide_visibility(0.75, ["apply_link_broken"])
    assert action == "hide"


def test_fp_rate_on_active_good_meets_gate():
    """FP = active-good receiving score >= 0.3 should be low."""
    good_count = 0
    fp_count = 0

    for ex in GOLD_EXAMPLES:
        if ex["ghost_label"] != "active-good":
            continue
        good_count += 1
        job = _make_canonical(ex)
        score, _ = compute_ghost_score(job)
        if score >= 0.3:
            fp_count += 1

    fp_rate = fp_count / max(good_count, 1)
    # v1 heuristic is conservative on primary-like data
    assert fp_rate <= 0.20, f"FP rate on active-good = {fp_rate:.2f} too high"


def test_catch_rate_on_clear_ghosts():
    """Catch rate on stale + suspicious_evergreen >= 0.5"""
    ghost_count = 0
    caught = 0

    for ex in GOLD_EXAMPLES:
        if ex["ghost_label"] not in ("stale", "suspicious_evergreen"):
            continue
        ghost_count += 1
        job = _make_canonical(ex)
        score, _ = compute_ghost_score(job)
        if score >= 0.5:
            caught += 1

    rate = caught / max(ghost_count, 1)
    assert rate >= 0.50, f"catch rate on ghosts = {rate:.2f} < 0.50"


def test_all_nonzero_scores_have_reasons():
    for ex in GOLD_EXAMPLES:
        job = _make_canonical(ex)
        score, reasons = compute_ghost_score(job)
        if score > 0.05:
            assert reasons and reasons[0] != "no_ghost_signals_detected"
