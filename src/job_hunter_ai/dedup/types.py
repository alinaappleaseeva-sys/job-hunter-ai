"""Types for deduplication and canonical job creation (Phase 5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from job_hunter_ai.common.models import CanonicalJob
from job_hunter_ai.common.models import CanonicalMergeEvent
from job_hunter_ai.common.models import NormalizedJobPosting


@dataclass(slots=True)
class DedupMatch:
    """One pairwise or group match decision for audit."""

    posting_id: str
    matched_to: str  # canonical or other posting id
    match_type: str  # "exact" | "heuristic"
    confidence: float
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DedupResult:
    """Outcome of a dedup run over a batch of postings."""

    canonicals: list[CanonicalJob] = field(default_factory=list)
    matches: list[DedupMatch] = field(default_factory=list)
    canonical_count: int = 0
    posting_count: int = 0
    merged_groups: int = 0

    @property
    def merge_rate(self) -> float:
        if self.posting_count <= 0:
            return 0.0
        merged_postings = sum(c.active_posting_count for c in self.canonicals)
        return merged_postings / self.posting_count
