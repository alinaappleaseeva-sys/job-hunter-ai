"""Ghost-job detector v1 (Phase 7).

Rule-based, fully explainable.
Starts with explicit signals from the spec.
Default policy prefers downrank over hide.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from job_hunter_ai.common.models import CanonicalJob

# v1 signal weights (from spec, simplified for MVP)
SIGNAL_WEIGHTS = {
    "apply_link_missing": 0.25,
    "apply_link_broken": 0.35,
    "apply_link_redirects_to_non_job_page": 0.30,
    "secondary_source_only": 0.20,
    "no_confirmed_primary_source": 0.25,
    "stale_secondary_listing": 0.20,
    "old_posting_age": 0.15,
    "repost_pattern": 0.15,
    "freshness_mismatch": 0.10,
}

DEFAULT_HIDE_THRESHOLD = 0.60
DEFAULT_DOWNRANK_THRESHOLD = 0.30


def _days_since(dt: datetime | None) -> float:
    if dt is None:
        return 999.0
    now = datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    delta = now - dt
    return max(0.0, delta.days + delta.seconds / 86400)


def _infer_basic_signals(job: CanonicalJob) -> dict[str, bool]:
    signals: dict[str, bool] = {}
    age_days = _days_since(job.canonical_posted_at)
    if age_days > 90:
        signals["old_posting_age"] = True
    if getattr(job, "source_count", 1) >= 2 or age_days > 60:
        signals["secondary_source_only"] = True
        signals["no_confirmed_primary_source"] = True
    if age_days > 60:
        signals["stale_secondary_listing"] = True
    if getattr(job, "source_count", 1) >= 3 and age_days > 30:
        signals["repost_pattern"] = True
    return signals


def compute_ghost_score(
    job: CanonicalJob,
    extra_signals: dict[str, bool] | None = None,
) -> tuple[float, list[str]]:
    """Return (ghost_score 0.0-1.0, list of active signal reasons).

    Score is sum of weights for detected signals, capped at 1.0.
    """
    signals = _infer_basic_signals(job)
    if extra_signals:
        signals.update(extra_signals)

    active_reasons: list[str] = []
    score = 0.0

    for sig, active in signals.items():
        if active and sig in SIGNAL_WEIGHTS:
            w = SIGNAL_WEIGHTS[sig]
            score += w
            active_reasons.append(f"{sig} (+{w:.2f})")

    score = min(1.0, round(score, 3))

    if not active_reasons and score == 0.0:
        active_reasons.append("no_ghost_signals_detected")

    return score, active_reasons


def decide_visibility(
    ghost_score: float,
    reasons: list[str],
) -> tuple[str, str]:
    """Return (action, policy_reason).

    Actions: show | downrank | hide
    """
    if ghost_score >= DEFAULT_HIDE_THRESHOLD:
        return "hide", f"ghost_score={ghost_score} >= {DEFAULT_HIDE_THRESHOLD} " + "; ".join(reasons[:2])
    if ghost_score >= DEFAULT_DOWNRANK_THRESHOLD:
        return "downrank", f"ghost_score={ghost_score} >= {DEFAULT_DOWNRANK_THRESHOLD} " + "; ".join(reasons[:2])
    return "show", "low_ghost_risk"


def apply_ghost_penalty(
    ranked_jobs: list[Any],  # list[RankedJob] at runtime
    downrank_factor: float = 0.55,
) -> list[Any]:
    """Adjust scores in-place for ghosted jobs.

    Used by ranking/delivery pipeline.
    Returns the (possibly modified) list.
    """
    from job_hunter_ai.common.models import RankedJob  # local import to avoid cycles

    for rj in ranked_jobs:
        if not isinstance(rj, RankedJob):
            continue
        job = rj.canonical_job
        ghost_score, reasons = compute_ghost_score(job)

        # attach to the canonical for downstream use
        job.ghost_score = ghost_score

        if ghost_score >= DEFAULT_DOWNRANK_THRESHOLD:
            # penalize total_score
            penalty = 1.0 - (1.0 - downrank_factor) * min(ghost_score / 0.8, 1.0)
            rj.score_breakdown.total_score *= penalty
            # add explanation
            rj.score_breakdown.explanations.append(
                type(rj.score_breakdown.explanations[0])(
                    component="ghost_penalty",
                    score=ghost_score,
                    reasons=[f"ghost_score={ghost_score:.2f}: {r}" for r in reasons[:2]],
                )
            )
            # re-sort later if needed by caller

    return ranked_jobs
