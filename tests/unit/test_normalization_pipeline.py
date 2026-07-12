"""Unit tests for the normalization pipeline skeleton (Step 4.2)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from job_hunter_ai.common.models import NormalizedJobPosting
from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.normalization import (
    BaseMapper,
    normalize_postings,
    normalize_record,
    register_mapper,
    resolve_provider,
)
from job_hunter_ai.storage import MemoryJobStorage

NOW = datetime(2026, 7, 12, tzinfo=timezone.utc)


def _raw_record(**overrides: object) -> RawSourceRecord:
    base = dict(
        source_name="greenhouse:stripe",
        source_type="ats",
        record_type="job_posting",
        external_id="7954688",
        source_url="https://stripe.com/jobs/7954688",
        fetched_at=NOW,
        discovered_at=NOW,
        payload={"title": "Product Manager", "content": "<p>Build</p>"},
        content_hash="raw-hash",
        cursor_value=None,
        metadata={"provider": "greenhouse"},
    )
    base.update(overrides)
    return RawSourceRecord(**base)


class _StubMapper(BaseMapper):
    provider = "greenhouse"

    def normalize(self, record: RawSourceRecord) -> NormalizedJobPosting:
        return NormalizedJobPosting(
            posting_id="stub-posting",
            source_name=record.source_name,
            source_type=record.source_type,
            external_id=record.external_id,
            source_url=record.source_url,
            company_name="Stripe",
            company_domain="stripe.com",
            title_raw="Product Manager",
            title_normalized="product manager",
            description_raw=None,
            description_text="Build",
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
            discovered_at=record.discovered_at,
            normalized_at=NOW,
            content_hash=record.content_hash,
            parse_status="partial",
            parse_warnings=["employment_type_missing"],
        )


@pytest.fixture(autouse=True)
def _clear_registry() -> None:
    from job_hunter_ai.normalization import registry

    registry._MAPPERS.clear()
    yield
    registry._MAPPERS.clear()


def test_resolve_provider_splits_source_name() -> None:
    assert resolve_provider("greenhouse:stripe") == "greenhouse"
    assert resolve_provider("lever:leverdemo") == "lever"


def test_unknown_source_returns_failed_without_mapper() -> None:
    item = normalize_record(_raw_record(source_name="greenhouse:stripe"))
    assert item.posting.parse_status == "failed"
    assert "unsupported_provider" in item.posting.parse_warnings
    assert item.diagnostics.provider == "greenhouse"
    assert item.diagnostics.mapper_name is None


def test_unknown_provider_slug_returns_failed() -> None:
    item = normalize_record(_raw_record(source_name="unknown:acme"))
    assert item.posting.parse_status == "failed"
    assert item.diagnostics.provider == "unknown"


def test_registered_mapper_produces_posting() -> None:
    register_mapper(_StubMapper())
    item = normalize_record(_raw_record())
    assert item.posting.parse_status == "partial"
    assert item.posting.title_normalized == "product manager"
    assert item.diagnostics.mapper_name == "_StubMapper"


def test_normalize_postings_aggregates_counts() -> None:
    register_mapper(_StubMapper())
    records = [
        _raw_record(external_id="1"),
        _raw_record(source_name="unknown:x", external_id="2"),
    ]
    result = normalize_postings(records)
    assert result.total == 2
    assert result.partial == 1
    assert result.failed == 1
    assert result.parse_rate == 0.5


def test_normalize_with_store_persists_lineage() -> None:
    register_mapper(_StubMapper())
    store = MemoryJobStorage()
    item = normalize_record(_raw_record(), store=store)

    assert item.persisted is True
    assert item.raw_record_id is not None
    assert item.posting_id == "stub-posting"

    loaded_raw = store.get_raw(item.raw_record_id)
    assert loaded_raw is not None
    assert loaded_raw.record.external_id == "7954688"

    loaded_norm = store.get_normalized(item.posting_id)
    assert loaded_norm is not None
    assert loaded_norm.raw_record_id == item.raw_record_id
    assert loaded_norm.posting.title_normalized == "product manager"


def test_mapper_exception_surfaces_as_failed() -> None:
    class _BrokenMapper(BaseMapper):
        provider = "greenhouse"

        def normalize(self, record: RawSourceRecord) -> NormalizedJobPosting:
            raise ValueError("boom")

    register_mapper(_BrokenMapper())
    item = normalize_record(_raw_record())
    assert item.posting.parse_status == "failed"
    assert "mapper_error" in item.posting.parse_warnings
    assert item.diagnostics.error_type == "ValueError"