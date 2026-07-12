"""Unit tests for in-memory job storage."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from job_hunter_ai.common.models import CanonicalJob
from job_hunter_ai.common.models import CanonicalMergeEvent
from job_hunter_ai.common.models import NormalizedJobPosting
from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.storage import MemoryJobStorage

NOW = datetime(2026, 7, 12, tzinfo=timezone.utc)


def _raw_record(**overrides: object) -> RawSourceRecord:
    base = dict(
        source_name="greenhouse:stripe",
        source_type="ats",
        record_type="job_posting",
        external_id="123",
        source_url="https://stripe.com/jobs/123",
        fetched_at=NOW,
        discovered_at=NOW,
        payload={"title": "Product Manager"},
        content_hash="abc",
        cursor_value=None,
        metadata={},
    )
    base.update(overrides)
    return RawSourceRecord(**base)


def _normalized_posting(**overrides: object) -> NormalizedJobPosting:
    base = dict(
        posting_id="",
        source_name="greenhouse:stripe",
        source_type="ats",
        external_id="123",
        source_url="https://stripe.com/jobs/123",
        company_name="Stripe",
        company_domain="stripe.com",
        title_raw="Product Manager",
        title_normalized="product manager",
        description_raw=None,
        description_text="Build payments",
        location_raw="San Francisco, CA",
        location_country="US",
        location_region="CA",
        location_city="San Francisco",
        remote_mode="onsite",
        employment_type=None,
        seniority=None,
        role_family="product",
        market="fintech",
        compensation_min=None,
        compensation_max=None,
        compensation_currency=None,
        posted_at=NOW,
        discovered_at=NOW,
        normalized_at=NOW,
        content_hash="norm-abc",
        parse_status="partial",
        parse_warnings=["employment_type_missing"],
    )
    base.update(overrides)
    return NormalizedJobPosting(**base)


def test_save_and_get_raw_round_trip() -> None:
    store = MemoryJobStorage()
    raw_id = store.save_raw(_raw_record())

    loaded = store.get_raw(raw_id)
    assert loaded is not None
    assert loaded.raw_record_id == raw_id
    assert loaded.record.external_id == "123"
    assert loaded.record.source_name == "greenhouse:stripe"


def test_get_raw_returns_none_for_unknown_id() -> None:
    store = MemoryJobStorage()
    assert store.get_raw("missing") is None


def test_save_normalized_links_to_raw_record() -> None:
    store = MemoryJobStorage()
    raw_id = store.save_raw(_raw_record())
    posting_id = store.save_normalized(_normalized_posting(), raw_record_id=raw_id)

    loaded = store.get_normalized(posting_id)
    assert loaded is not None
    assert loaded.posting_id == posting_id
    assert loaded.raw_record_id == raw_id
    assert loaded.posting.title_normalized == "product manager"


def test_save_normalized_requires_existing_raw_record() -> None:
    store = MemoryJobStorage()
    with pytest.raises(KeyError, match="Unknown raw_record_id"):
        store.save_normalized(_normalized_posting(), raw_record_id="nope")


def test_list_unlinked_raw_excludes_normalized_records() -> None:
    store = MemoryJobStorage()
    raw_linked = store.save_raw(_raw_record(external_id="linked"))
    raw_orphan = store.save_raw(_raw_record(external_id="orphan"))
    store.save_normalized(_normalized_posting(external_id="linked"), raw_record_id=raw_linked)

    unlinked = store.list_unlinked_raw()
    assert len(unlinked) == 1
    assert unlinked[0].record.external_id == "orphan"
    assert unlinked[0].raw_record_id == raw_orphan


def test_list_by_source_filters_correctly() -> None:
    store = MemoryJobStorage()
    gh_raw = store.save_raw(_raw_record(source_name="greenhouse:stripe"))
    store.save_raw(_raw_record(source_name="lever:demo", external_id="lv-1"))
    store.save_normalized(_normalized_posting(), raw_record_id=gh_raw)

    assert len(store.list_raw_by_source("greenhouse:stripe")) == 1
    assert len(store.list_raw_by_source("lever:demo")) == 1
    assert len(store.list_normalized_by_source("greenhouse:stripe")) == 1
    assert len(store.list_normalized_by_source("lever:demo")) == 0


def test_save_normalized_uses_provided_posting_id() -> None:
    store = MemoryJobStorage()
    raw_id = store.save_raw(_raw_record())
    posting_id = store.save_normalized(
        _normalized_posting(posting_id="fixed-posting-id"),
        raw_record_id=raw_id,
    )
    assert posting_id == "fixed-posting-id"


def test_clear_resets_store() -> None:
    store = MemoryJobStorage()
    raw_id = store.save_raw(_raw_record())
    store.save_normalized(_normalized_posting(), raw_record_id=raw_id)
    store.clear()
    assert store.get_raw(raw_id) is None
    assert store.list_unlinked_raw() == []


# --- Phase 5 canonical / dedup storage tests ---


def _canonical(**overrides: object) -> CanonicalJob:
    base = dict(
        canonical_job_id=str(uuid4()),
        primary_posting_id="p-1",
        company_name="TestCo",
        company_domain="test.co",
        title_normalized="engineer",
        role_family=None,
        seniority=None,
        market=None,
        remote_mode="remote",
        employment_type=None,
        location_country=None,
        location_region=None,
        location_city=None,
        compensation_min=None,
        compensation_max=None,
        compensation_currency=None,
        canonical_posted_at=NOW,
        first_seen_at=NOW,
        last_seen_at=NOW,
        active_posting_count=1,
        source_count=1,
        ghost_score=None,
        canonical_status="active",
        merge_confidence=0.9,
        merge_reasons=["exact_title_company"],
    )
    base.update(overrides)
    return CanonicalJob(**base)  # type: ignore[arg-type]


def test_save_and_link_canonical_roundtrip() -> None:
    store = MemoryJobStorage()
    raw_id = store.save_raw(_raw_record())
    pid = store.save_normalized(_normalized_posting(posting_id="p-1"), raw_record_id=raw_id)

    can = _canonical(primary_posting_id=pid)
    cid = store.save_canonical(can)
    store.link_posting_to_canonical(canonical_job_id=cid, posting_id=pid)

    loaded = store.get_canonical(cid)
    assert loaded is not None
    assert loaded.canonical_job_id == cid
    assert loaded.canonical.title_normalized == "engineer"

    linked = store.list_postings_for_canonical(cid)
    assert len(linked) == 1
    assert linked[0].posting_id == pid

    assert store.get_canonical_for_posting(pid) == cid


def test_save_merge_event_and_list() -> None:
    store = MemoryJobStorage()
    can = _canonical()
    cid = store.save_canonical(can)

    ev = CanonicalMergeEvent(
        canonical_job_id=cid,
        posting_id="p-1",
        merged_at=NOW,
        merge_confidence=0.95,
        merge_reasons=["exact_title_company"],
    )
    store.save_merge_event(ev)

    events = store.list_merge_events_for_canonical(cid)
    assert len(events) == 1
    assert events[0].posting_id == "p-1"
