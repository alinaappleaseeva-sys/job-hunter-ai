"""Connector quality helpers.

This module turns the agreed source-quality formula into runnable code:

    quality = parse_rate * field_coverage * (1 - ghost_rate)

The first implementation keeps the logic intentionally simple and explicit so
we can iterate on weights and ghost thresholds without hiding behavior.
"""

from __future__ import annotations

from job_hunter_ai.common.models import ConnectorQuality
from job_hunter_ai.common.models import NormalizedJobPosting


FIELD_COVERAGE_WEIGHTS: dict[str, float] = {
    "title_normalized": 0.20,
    "company_name": 0.15,
    "description_text": 0.15,
    "posted_at": 0.15,
    "location_raw": 0.10,
    "remote_mode": 0.10,
    "source_url": 0.10,
    "employment_type": 0.05,
}


def is_ghost_or_stale(posting: NormalizedJobPosting, *, ghost_threshold: float = 0.6) -> bool:
    """Return whether the posting should count as ghost-like for source quality.

    The first version uses simple source-side signals only:
    - failed parsing counts as unusable
    - warning markers can explicitly flag ghost or stale suspicion
    """

    if posting.parse_status == "failed":
        return True

    warnings = {warning.lower() for warning in posting.parse_warnings}
    if "ghost" in warnings or "stale" in warnings:
        return True

    # Reserved for future numeric or score-based inputs.
    _ = ghost_threshold
    return False


def field_coverage(posting: NormalizedJobPosting) -> float:
    """Compute weighted completeness for one normalized posting."""

    score = 0.0
    for field_name, weight in FIELD_COVERAGE_WEIGHTS.items():
        value = getattr(posting, field_name)
        if value is not None and value != "":
            score += weight
    return score


def ghost_rate(postings: list[NormalizedJobPosting], *, ghost_threshold: float = 0.6) -> float:
    """Compute ghost-like share across normalized postings."""

    if not postings:
        return 0.0
    ghost_count = sum(is_ghost_or_stale(posting, ghost_threshold=ghost_threshold) for posting in postings)
    return ghost_count / len(postings)


def parse_rate(*, raw_record_count: int, normalized_postings_count: int) -> float:
    """Compute the share of raw records that successfully normalized."""

    if raw_record_count <= 0:
        return 0.0
    return normalized_postings_count / raw_record_count


def average_field_coverage(postings: list[NormalizedJobPosting]) -> float:
    """Compute mean field coverage across normalized postings."""

    if not postings:
        return 0.0
    return sum(field_coverage(posting) for posting in postings) / len(postings)


def compute_quality(
    *,
    raw_record_count: int,
    postings: list[NormalizedJobPosting],
    ghost_threshold: float = 0.6,
) -> ConnectorQuality:
    """Compute the agreed connector quality score."""

    pr = parse_rate(raw_record_count=raw_record_count, normalized_postings_count=len(postings))
    fc = average_field_coverage(postings)
    gr = ghost_rate(postings, ghost_threshold=ghost_threshold)
    quality = pr * fc * (1 - gr)
    return ConnectorQuality(
        parse_rate=pr,
        field_coverage=fc,
        ghost_rate=gr,
        quality=quality,
    )

