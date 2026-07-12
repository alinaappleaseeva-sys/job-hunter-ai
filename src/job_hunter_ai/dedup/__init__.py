"""Dedup and Canonical Jobs (Phase 5).

Provides models re-exports, deduplication service, and types.
"""

from job_hunter_ai.common.models import CanonicalJob
from job_hunter_ai.common.models import CanonicalMergeEvent
from job_hunter_ai.dedup.service import deduplicate_postings
from job_hunter_ai.dedup.types import DedupMatch
from job_hunter_ai.dedup.types import DedupResult

__all__ = [
    "CanonicalJob",
    "CanonicalMergeEvent",
    "DedupMatch",
    "DedupResult",
    "deduplicate_postings",
]
