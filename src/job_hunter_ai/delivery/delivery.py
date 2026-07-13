"""Delivery UX v1 (Phase 9).

Turns RankedJobs into usable output (digest / inbox) and records user actions
with full traceability to ranking + ghost decisions.

No silent actions. Every action produces a FeedbackEvent.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Any

from job_hunter_ai.common.models import (
    CandidateProfile,
    FeedbackEvent,
    JobScoreBreakdown,
    RankedJob,
    ScoreExplanation,
)


def build_digest(
    profile: CandidateProfile,
    ranked_jobs: list[RankedJob],
    limit: int = 20,
) -> dict[str, Any]:
    """Simple digest payload for delivery.

    Includes top ranked jobs with explanations exposed.
    """
    items = []
    for rj in sorted(ranked_jobs, key=lambda x: x.score_breakdown.total_score, reverse=True)[:limit]:
        items.append({
            "canonical_job_id": rj.canonical_job.canonical_job_id,
            "title": rj.canonical_job.title_normalized,
            "company": rj.canonical_job.company_name,
            "total_score": rj.score_breakdown.total_score,
            "explanations": [
                {"component": e.component, "score": e.score, "reasons": e.reasons}
                for e in rj.score_breakdown.explanations
            ],
            "ghost_score": rj.canonical_job.ghost_score,
            "rank": rj.rank,
        })
    return {
        "profile_id": profile.profile_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "count": len(items),
        "jobs": items,
    }


def apply_action(
    ranked_job: RankedJob,
    profile_id: str,
    action: str,
    reason: str | None = None,
) -> FeedbackEvent:
    """Record a user action with full trace.

    Actions: relevant, not_relevant, duplicate, ghost_likely, applied
    """
    allowed = {"relevant", "not_relevant", "duplicate", "ghost_likely", "applied"}
    if action not in allowed:
        raise ValueError(f"invalid action: {action}")

    event = FeedbackEvent(
        event_id=str(uuid.uuid4()),
        profile_id=profile_id,
        canonical_job_id=ranked_job.canonical_job.canonical_job_id,
        action=action,
        reason=reason,
        score_breakdown=ranked_job.score_breakdown,
        explanations=list(ranked_job.score_breakdown.explanations),
        ghost_score=ranked_job.canonical_job.ghost_score,
        metadata={"source": "delivery_v1"},
    )
    return event


def persist_feedback(event: FeedbackEvent, storage: Any | None = None) -> str:
    """Persist feedback event.

    MVP: if storage has add_feedback, use it; else return id (caller can store).
    In real impl this would go to DB via repository.
    """
    if storage is not None and hasattr(storage, "add_feedback"):
        storage.add_feedback(event)
    return event.event_id
