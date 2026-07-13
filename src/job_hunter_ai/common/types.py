"""Backward-compatible re-export layer for common data models.

New code should import shared models from ``job_hunter_ai.common.models``.
This module exists only to keep early imports working while the codebase
migrates to the canonical import path.
"""

from .models import CanonicalJob
from .models import CanonicalMergeEvent
from .models import CandidateProfile
from .models import ConnectorQuality
from .models import FeedbackEvent
from .models import JobScoreBreakdown
from .models import NormalizedJobPosting
from .models import RankedJob
from .models import RawSourceRecord
from .models import ScoreExplanation
from .models import SourceRunResult

__all__ = [
    "CanonicalJob",
    "CanonicalMergeEvent",
    "CandidateProfile",
    "ConnectorQuality",
    "FeedbackEvent",
    "JobScoreBreakdown",
    "NormalizedJobPosting",
    "RankedJob",
    "RawSourceRecord",
    "ScoreExplanation",
    "SourceRunResult",
]
