"""Ranking package (Phase 6+).

Public API:
- rank_jobs(profile, jobs) -> list[RankedJob]
- compute_score_breakdown
- CandidateProfile etc. re-exported for convenience
"""

from job_hunter_ai.common.models import CandidateProfile, JobScoreBreakdown, RankedJob, ScoreExplanation
from job_hunter_ai.ranking.ranking import (
    compute_score_breakdown,
    rank_jobs,
    simple_chrono_baseline,
)

__all__ = [
    "CandidateProfile",
    "JobScoreBreakdown",
    "RankedJob",
    "ScoreExplanation",
    "compute_score_breakdown",
    "rank_jobs",
    "simple_chrono_baseline",
]
