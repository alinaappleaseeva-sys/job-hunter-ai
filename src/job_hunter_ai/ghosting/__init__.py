"""Ghosting / ghost-job detection (Phase 7+).

Public API:
- compute_ghost_score
- decide_visibility
- apply_ghost_penalty
"""

from job_hunter_ai.ghosting.ghosting import (
    apply_ghost_penalty,
    compute_ghost_score,
    decide_visibility,
)

__all__ = [
    "apply_ghost_penalty",
    "compute_ghost_score",
    "decide_visibility",
]
