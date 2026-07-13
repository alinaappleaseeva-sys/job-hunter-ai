"""Delivery package (Phase 9+).

Public API:
- build_digest
- apply_action -> FeedbackEvent
- persist_feedback
"""

from job_hunter_ai.common.models import FeedbackEvent
from job_hunter_ai.delivery.delivery import apply_action, build_digest, persist_feedback

__all__ = ["FeedbackEvent", "apply_action", "build_digest", "persist_feedback"]
