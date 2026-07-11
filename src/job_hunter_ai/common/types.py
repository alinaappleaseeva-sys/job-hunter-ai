"""Backward-compatible re-export layer for common data models.

New code should import shared models from ``job_hunter_ai.common.models``.

This module exists only to keep early imports working while the codebase
migrates to the canonical import path.
"""

from .models import CanonicalJob
from .models import CanonicalMergeEvent
from .models import ConnectorQuality
from .models import NormalizedJobPosting
from .models import RawSourceRecord
from .models import SourceRunResult

__all__ = [
    "CanonicalJob",
    "CanonicalMergeEvent",
    "ConnectorQuality",
    "NormalizedJobPosting",
    "RawSourceRecord",
    "SourceRunResult",
]
