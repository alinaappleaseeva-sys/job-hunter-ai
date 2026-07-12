"""Unit tests for in-memory job storage."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

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