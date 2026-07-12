"""Unit tests for dedup service (Phase 5).

Covers:
- exact match dedup (domain+title and content_hash)
- basic heuristic (title+company similarity)
- primary posting selection
- linkage when store is provided
- merge events
- single postings become their own canonical
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from job_hunter_ai.common.models import NormalizedJobPosting
from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.dedup import deduplicate_postings
from job_hunter_ai.dedup.service import _is_exact_match, _is_heuristic_match
from job_hunter_ai.storage import MemoryJobStorage

NOW = datetime(2026, 7, 12, 10, 0, tzinfo=timezone.utc)

def _raw_record(**overrides: object) -> RawSourceRecord:
    base = dict(
        source_name="x:acme",
        source_type="ats",
        record_type="job_posting",
        external_id="raw-123",
        source_url=None,
        fetched_at=NOW,
        discovered_at=NOW,
        payload={"title": "Eng"},
        content_hash=None,
        cursor_value=None,
        metadata={},
    )
    base.update(overrides)
    return RawSourceRecord(**base)

def _posting(**overrides: object) -> NormalizedJobPosting:
    base = dict(
        posting_id=str(uuid4()),
        source_name="greenhouse:acme",
        source_type="ats",
        external_id="123",
        source_url="https://acme.com/jobs/123",
        company_name="Acme Corp",
        company_domain="acme.com",
        title_raw="Senior Backend Engineer",
        title_normalized="senior backend engineer",
        description_raw=None,
        description_text="Build scalable systems",
        location_raw="Remote",
        location_country=None,
        location_region=None,
        location_city=None,
        remote_mode="remote",
        employment_type="full-time",
        seniority="senior",
        role_family="engineering",
        market="infra",
        compensation_min=None,
        compensation_max=None,
        compensation_currency=None,
        posted_at=NOW,
        discovered_at=NOW,
        normalized_at=NOW,
        content_hash=None,
        parse_status="parsed",
        parse_warnings=[],
    )
    base.update(overrides)
    return NormalizedJobPosting(**base)  # type: ignore[arg-type]


def test_exact_match_same_domain_title() -> None:
    p1 = _posting(company_domain="acme.com", title_normalized="senior backend engineer", content_hash=None)
    p2 = _posting(company_domain="acme.com", title_normalized="senior backend engineer", content_hash="h2", external_id="dup")
    assert _is_exact_match(p1, p2) is True


def test_exact_match_by_content_hash() -> None:
    p1 = _posting(content_hash="samehash123")
    p2 = _posting(content_hash="samehash123", company_domain=None, title_normalized=None)
    assert _is_exact_match(p1, p2) is True


def test_heuristic_match_title_company_similar() -> None:
    p1 = _posting(company_name="Acme", company_domain="acme.com", title_normalized="senior backend engineer")
    p2 = _posting(
        company_name="Acme Inc",
        company_domain=None,
        title_normalized="senior backend engineer",
        source_name="lever:acme",
        source_type="ats",
    )
    assert _is_heuristic_match(p1, p2) is True


def test_no_match_different_company() -> None:
    p1 = _posting(company_name="Acme", company_domain=None)
    p2 = _posting(company_name="Zeta Quantum", company_domain=None, title_normalized="senior backend engineer")
    assert _is_exact_match(p1, p2) is False
    assert _is_heuristic_match(p1, p2) is False


def test_dedup_exact_groups_into_one_canonical() -> None:
    p1 = _posting(company_domain="stripe.com", title_normalized="product manager")
    p2 = _posting(
        company_domain="stripe.com",
        title_normalized="product manager",
        source_name="ashby:stripe",
        source_type="ats",
        external_id="p2",
    )
    result = deduplicate_postings([p1, p2])
    assert result.canonical_count == 1
    assert result.posting_count == 2
    assert result.merged_groups == 1
    can = result.canonicals[0]
    assert can.company_domain == "stripe.com"
    assert can.title_normalized == "product manager"
    assert can.active_posting_count == 2
    assert can.source_count == 2
    assert "exact_title_company" in can.merge_reasons


def test_dedup_heuristic_merges_similar() -> None:
    p1 = _posting(company_name="OpenAI", title_normalized="ml engineer", company_domain="openai.com")
    p2 = _posting(
        company_name="Open AI",
        title_normalized="ml engineering",
        company_domain=None,
        source_name="wellfound:openai",
        source_type="job_board",
    )
    result = deduplicate_postings([p1, p2])
    assert result.canonical_count == 1
    assert result.merged_groups == 1
    assert "title_company_similarity" in result.canonicals[0].merge_reasons


def test_dedup_single_posting_is_own_canonical() -> None:
    p = _posting()
    result = deduplicate_postings([p])
    assert result.canonical_count == 1
    assert result.merged_groups == 0
    assert result.canonicals[0].active_posting_count == 1
    assert "single_posting" in result.canonicals[0].merge_reasons


def test_dedup_with_store_persists_links_and_events() -> None:
    store = MemoryJobStorage()

    # Properly persist raw + normalized first (required for list_postings_for_canonical to return full objects)
    raw1 = _raw_record(external_id="p1-raw", source_name="x:acme")
    raw_id1 = store.save_raw(raw1)
    p1 = _posting(posting_id="p1", company_domain="x.com", title_normalized="eng")
    store.save_normalized(p1, raw_record_id=raw_id1)

    raw2 = _raw_record(external_id="p2-raw", source_name="x:board")
    raw_id2 = store.save_raw(raw2)
    p2 = _posting(posting_id="p2", company_domain="x.com", title_normalized="eng", source_name="x:board")
    store.save_normalized(p2, raw_record_id=raw_id2)

    result = deduplicate_postings([p1, p2], store=store)

    assert result.canonical_count == 1
    cid = result.canonicals[0].canonical_job_id

    stored_can = store.get_canonical(cid)
    assert stored_can is not None

    linked = store.list_postings_for_canonical(cid)
    assert len(linked) == 2
    posting_ids = {lp.posting_id for lp in linked}
    assert "p1" in posting_ids and "p2" in posting_ids

    events = store.list_merge_events_for_canonical(cid)
    assert len(events) == 2
    assert all(e.canonical_job_id == cid for e in events)


def test_primary_prefers_ats_source() -> None:
    # non-ats first in list
    board = _posting(
        posting_id="board",
        source_type="job_board",
        company_domain="acme.com",
        title_normalized="eng",
        description_text=None,
    )
    ats = _posting(
        posting_id="ats",
        source_type="ats",
        company_domain="acme.com",
        title_normalized="eng",
        description_text="lots of detail here",
    )
    result = deduplicate_postings([board, ats])
    can = result.canonicals[0]
    assert can.primary_posting_id == "ats"


def test_different_jobs_not_merged() -> None:
    p1 = _posting(company_domain="a.com", title_normalized="backend")
    p2 = _posting(company_domain="a.com", title_normalized="frontend designer")
    result = deduplicate_postings([p1, p2])
    assert result.canonical_count == 2
    assert result.merged_groups == 0
