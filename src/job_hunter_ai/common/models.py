"""Shared dataclasses for core pipeline entities.

This module is the canonical import location for shared pipeline models.

The dataclasses intentionally stay lightweight. They represent the agreed
shapes from the specs and give the rest of the codebase one stable import
surface for the first implementation wave.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

JsonDict = dict[str, Any]
StringList = list[str]


@dataclass(slots=True)
class RawSourceRecord:
    """Standard raw record emitted by every connector.

    See docs/specs/source-contract.md for semantics.
    """

    source_name: str
    source_type: str
    record_type: str
    external_id: str | None
    source_url: str | None
    fetched_at: datetime
    discovered_at: datetime | None
    payload: JsonDict
    content_hash: str | None
    cursor_value: str | None
    metadata: JsonDict = field(default_factory=dict)


@dataclass(slots=True)
class SourceRunResult:
    """Summary of a single connector run."""

    source_name: str
    started_at: datetime
    finished_at: datetime
    success: bool
    records_fetched: int
    records_emitted: int
    records_persisted: int
    cursor_before: str | None
    cursor_after: str | None
    error_type: str | None = None
    error_message: str | None = None
    run_metadata: JsonDict = field(default_factory=dict)


@dataclass(slots=True)
class ConnectorQuality:
    """Runnable quality score for a connector run.

    quality = parse_rate * field_coverage * (1 - ghost_rate)
    """

    parse_rate: float
    field_coverage: float
    ghost_rate: float
    quality: float


@dataclass(slots=True)
class NormalizedJobPosting:
    """One source-specific posting normalized into the shared posting schema."""

    posting_id: str
    source_name: str
    source_type: str
    external_id: str | None
    source_url: str | None
    company_name: str | None
    company_domain: str | None
    title_raw: str | None
    title_normalized: str | None
    description_raw: str | None
    description_text: str | None
    location_raw: str | None
    location_country: str | None
    location_region: str | None
    location_city: str | None
    remote_mode: str | None
    employment_type: str | None
    seniority: str | None
    role_family: str | None
    market: str | None
    compensation_min: float | None
    compensation_max: float | None
    compensation_currency: str | None
    posted_at: datetime | None
    discovered_at: datetime | None
    normalized_at: datetime
    content_hash: str | None
    parse_status: str
    parse_warnings: StringList = field(default_factory=list)


@dataclass(slots=True)
class CanonicalJob:
    """One logical opening after dedup across postings and sources."""

    canonical_job_id: str
    primary_posting_id: str
    company_name: str | None
    company_domain: str | None
    title_normalized: str | None
    role_family: str | None
    seniority: str | None
    market: str | None
    remote_mode: str | None
    employment_type: str | None
    location_country: str | None
    location_region: str | None
    location_city: str | None
    compensation_min: float | None
    compensation_max: float | None
    compensation_currency: str | None
    canonical_posted_at: datetime | None
    first_seen_at: datetime
    last_seen_at: datetime
    active_posting_count: int
    source_count: int
    ghost_score: float | None
    canonical_status: str
    merge_confidence: float | None
    merge_reasons: StringList = field(default_factory=list)


@dataclass(slots=True)
class CanonicalMergeEvent:
    """Audit record explaining why a posting was linked into a canonical job."""

    canonical_job_id: str
    posting_id: str
    merged_at: datetime
    merge_confidence: float | None
    merge_reasons: StringList = field(default_factory=list)
    reviewer_override: bool = False


# === Phase 6: Candidate Profile and Ranking models (explainable heuristics v1) ===

@dataclass(slots=True)
class CandidateProfile:
    """Target persona used for personalized ranking.

    Defines the Jobs the candidate wants to perform (role + context).
    Keep lightweight and serializable.
    """

    profile_id: str
    target_role_families: StringList = field(default_factory=list)
    target_seniorities: StringList = field(default_factory=list)
    target_title_keywords: StringList = field(default_factory=list)
    remote_preference: str | None = None  # "remote" | "hybrid" | "onsite" | "any"
    preferred_locations: StringList = field(default_factory=list)
    min_compensation: float | None = None
    compensation_currency: str | None = None
    preferred_markets: StringList = field(default_factory=list)
    notes: str | None = None


@dataclass(slots=True)
class ScoreExplanation:
    """Single explainable component of a score for auditability."""

    component: str
    score: float
    reasons: StringList = field(default_factory=list)
    signals: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class JobScoreBreakdown:
    """Transparent per-component scores + total for one job vs one profile."""

    role_fit: float = 0.0
    seniority_fit: float = 0.0
    location_remote_fit: float = 0.0
    salary_fit: float = 0.0
    market_fit: float = 0.0
    total_score: float = 0.0
    explanations: list[ScoreExplanation] = field(default_factory=list)


@dataclass(slots=True)
class RankedJob:
    """Canonical job wrapped with its ranking result for a given profile."""

    canonical_job: CanonicalJob
    score_breakdown: JobScoreBreakdown
    rank: int | None = None
