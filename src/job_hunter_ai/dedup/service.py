"""Dedup and canonical job creation logic (Phase 5).

Exact match on (company_domain + title_normalized) or content_hash.
Basic heuristic on title + company name similarity using SequenceMatcher.

Links normalized postings to CanonicalJob via the storage repository when provided.
Creates merge audit events.
"""

from __future__ import annotations

import difflib
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

from job_hunter_ai.common.models import CanonicalJob
from job_hunter_ai.common.models import CanonicalMergeEvent
from job_hunter_ai.common.models import NormalizedJobPosting
from job_hunter_ai.dedup.types import DedupMatch, DedupResult
from job_hunter_ai.storage.repository import JobStorageRepository

logger = logging.getLogger(__name__)


def _normalize_for_compare(s: str | None) -> str | None:
    """Lowercase, collapse whitespace for comparison keys and similarity."""
    if s is None:
        return None
    s = " ".join(s.split()).strip().lower()
    return s or None


def _similarity(a: str | None, b: str | None) -> float:
    """Return 0..1 similarity using stdlib SequenceMatcher."""
    aa = _normalize_for_compare(a) or ""
    bb = _normalize_for_compare(b) or ""
    if not aa or not bb:
        return 0.0
    return difflib.SequenceMatcher(None, aa, bb).ratio()


def _is_exact_match(p1: NormalizedJobPosting, p2: NormalizedJobPosting) -> bool:
    """Exact match signal for dedup."""
    # content_hash is strong signal if present and equal
    if p1.content_hash and p2.content_hash and p1.content_hash == p2.content_hash:
        return True

    c1 = p1.company_domain or _normalize_for_compare(p1.company_name)
    c2 = p2.company_domain or _normalize_for_compare(p2.company_name)
    t1 = p1.title_normalized
    t2 = p2.title_normalized

    if c1 and c2 and t1 and t2:
        return c1 == c2 and t1 == t2
    return False


def _is_heuristic_match(
    p1: NormalizedJobPosting,
    p2: NormalizedJobPosting,
    *,
    title_threshold: float = 0.82,
    company_threshold: float = 0.60,
) -> bool:
    """Basic title + company similarity heuristic."""
    c1 = p1.company_domain or _normalize_for_compare(p1.company_name)
    c2 = p2.company_domain or _normalize_for_compare(p2.company_name)
    t1 = p1.title_normalized or _normalize_for_compare(p1.title_raw)
    t2 = p2.title_normalized or _normalize_for_compare(p2.title_raw)

    if not c1 or not c2 or not t1 or not t2:
        return False

    c_sim = _similarity(c1, c2)
    t_sim = _similarity(t1, t2)
    return c_sim >= company_threshold and t_sim >= title_threshold


def _compute_completeness(posting: NormalizedJobPosting) -> int:
    """Simple score for primary selection. Higher = better representative."""
    score = 0
    if posting.source_type in {"ats", "company_page"}:
        score += 20
    key_fields = [
        posting.company_name,
        posting.company_domain,
        posting.title_normalized,
        posting.description_text,
        posting.location_city or posting.location_raw,
        posting.remote_mode,
        posting.posted_at,
        posting.compensation_min,
        posting.seniority,
        posting.role_family,
    ]
    for f in key_fields:
        if f:
            score += 2
    # small bonus for having url
    if posting.source_url:
        score += 1
    return score


def _choose_primary_posting_id(postings: list[NormalizedJobPosting]) -> str:
    """Select the posting_id that should be the primary for the canonical."""
    if not postings:
        raise ValueError("Cannot choose primary from empty postings list")
    # stable sort by score desc, then by posting_id for determinism
    sorted_posts = sorted(
        postings,
        key=lambda p: (-_compute_completeness(p), p.posting_id or ""),
    )
    return sorted_posts[0].posting_id


def _aggregate_canonical_fields(
    postings: list[NormalizedJobPosting], primary_id: str
) -> dict[str, object]:
    """Pick consolidated values for the canonical, preferring primary then first non-null."""
    primary = next((p for p in postings if p.posting_id == primary_id), postings[0])

    def pick_first_non_null(field_name: str) -> object | None:
        for p in [primary] + postings:
            val = getattr(p, field_name, None)
            if val is not None:
                return val
        return None

    posted_ats = [p.posted_at for p in postings if p.posted_at is not None]
    canonical_posted = min(posted_ats) if posted_ats else None

    discovered = [p.discovered_at for p in postings if p.discovered_at is not None]
    first_seen = min(discovered) if discovered else datetime.now(UTC)
    last_seen = max(discovered) if discovered else first_seen

    source_names = {p.source_name for p in postings if p.source_name}
    company_names = [p.company_name for p in postings if p.company_name]
    domains = [p.company_domain for p in postings if p.company_domain]

    return {
        "company_name": pick_first_non_null("company_name"),
        "company_domain": pick_first_non_null("company_domain") or (domains[0] if domains else None),
        "title_normalized": pick_first_non_null("title_normalized"),
        "role_family": pick_first_non_null("role_family"),
        "seniority": pick_first_non_null("seniority"),
        "market": pick_first_non_null("market"),
        "remote_mode": pick_first_non_null("remote_mode"),
        "employment_type": pick_first_non_null("employment_type"),
        "location_country": pick_first_non_null("location_country"),
        "location_region": pick_first_non_null("location_region"),
        "location_city": pick_first_non_null("location_city"),
        "compensation_min": pick_first_non_null("compensation_min"),
        "compensation_max": pick_first_non_null("compensation_max"),
        "compensation_currency": pick_first_non_null("compensation_currency"),
        "canonical_posted_at": canonical_posted,
        "first_seen_at": first_seen,
        "last_seen_at": last_seen,
        "active_posting_count": len(postings),
        "source_count": len(source_names),
    }


def _make_canonical(
    cluster: list[NormalizedJobPosting],
    match_type: str,
    confidence: float,
) -> CanonicalJob:
    """Create a CanonicalJob for a cluster of postings that should be merged."""
    primary_id = _choose_primary_posting_id(cluster)
    fields = _aggregate_canonical_fields(cluster, primary_id)

    reasons = ["exact_title_company"] if match_type == "exact" else ["title_company_similarity"]
    if len(cluster) == 1:
        reasons = ["single_posting"]

    cid = str(uuid4())
    return CanonicalJob(
        canonical_job_id=cid,
        primary_posting_id=primary_id,
        company_name=fields["company_name"],  # type: ignore
        company_domain=fields["company_domain"],  # type: ignore
        title_normalized=fields["title_normalized"],  # type: ignore
        role_family=fields["role_family"],  # type: ignore
        seniority=fields["seniority"],  # type: ignore
        market=fields["market"],  # type: ignore
        remote_mode=fields["remote_mode"],  # type: ignore
        employment_type=fields["employment_type"],  # type: ignore
        location_country=fields["location_country"],  # type: ignore
        location_region=fields["location_region"],  # type: ignore
        location_city=fields["location_city"],  # type: ignore
        compensation_min=fields["compensation_min"],  # type: ignore
        compensation_max=fields["compensation_max"],  # type: ignore
        compensation_currency=fields["compensation_currency"],  # type: ignore
        canonical_posted_at=fields["canonical_posted_at"],  # type: ignore
        first_seen_at=fields["first_seen_at"],  # type: ignore
        last_seen_at=fields["last_seen_at"],  # type: ignore
        active_posting_count=fields["active_posting_count"],  # type: ignore
        source_count=fields["source_count"],  # type: ignore
        ghost_score=None,
        canonical_status="active",
        merge_confidence=confidence,
        merge_reasons=reasons,
    )


def deduplicate_postings(
    postings: Sequence[NormalizedJobPosting],
    *,
    store: JobStorageRepository | None = None,
) -> DedupResult:
    """Run deduplication: group postings into canonical jobs.

    Uses:
    - exact match (domain+title or content_hash)
    - basic heuristic (title+company similarity)

    When `store` is provided, creates canonicals, links postings, and writes
    CanonicalMergeEvent records.

    Returns structured DedupResult for inspection and evals.
    """
    if not postings:
        return DedupResult()

    clusters: list[list[NormalizedJobPosting]] = []
    match_types: list[str] = []

    for p in postings:
        placed = False
        for i, cluster in enumerate(clusters):
            rep = cluster[0]
            if _is_exact_match(p, rep):
                cluster.append(p)
                match_types.append("exact")
                placed = True
                break
            if _is_heuristic_match(p, rep):
                cluster.append(p)
                match_types.append("heuristic")
                placed = True
                break
        if not placed:
            clusters.append([p])
            match_types.append("single")

    canonicals: list[CanonicalJob] = []
    matches: list[DedupMatch] = []

    for idx, cluster in enumerate(clusters):
        if not cluster:
            continue

        is_multi = len(cluster) > 1
        match_type = "exact" if any(_is_exact_match(cluster[0], p) for p in cluster[1:]) else "heuristic"
        if not is_multi:
            match_type = "single"
        conf = 1.0 if match_type == "exact" else (0.78 if match_type == "heuristic" else 1.0)

        can = _make_canonical(cluster, match_type, conf)
        canonicals.append(can)

        if store is not None:
            store.save_canonical(can)
            for p in cluster:
                store.link_posting_to_canonical(
                    canonical_job_id=can.canonical_job_id, posting_id=p.posting_id
                )
                event = CanonicalMergeEvent(
                    canonical_job_id=can.canonical_job_id,
                    posting_id=p.posting_id,
                    merged_at=datetime.now(UTC),
                    merge_confidence=conf,
                    merge_reasons=can.merge_reasons,
                )
                store.save_merge_event(event)

        # record simple matches for the result (first posting as "rep")
        for p in cluster[1:]:
            matches.append(
                DedupMatch(
                    posting_id=p.posting_id,
                    matched_to=cluster[0].posting_id,
                    match_type=match_type,
                    confidence=conf,
                    reasons=list(can.merge_reasons),
                )
            )

    result = DedupResult(
        canonicals=canonicals,
        matches=matches,
        canonical_count=len(canonicals),
        posting_count=len(postings),
        merged_groups=sum(1 for c in clusters if len(c) > 1),
    )

    logger.info(
        "dedup complete: postings=%s canonicals=%s merged_groups=%s",
        result.posting_count,
        result.canonical_count,
        result.merged_groups,
    )
    return result
