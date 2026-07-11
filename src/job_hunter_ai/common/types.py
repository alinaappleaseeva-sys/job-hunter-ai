"""Backward-compatible re-export layer for common data models.

This module exists so early code can keep importing from
``job_hunter_ai.common.types`` while the canonical implementations live in
``job_hunter_ai.common.models``.
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

