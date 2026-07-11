from __future__ import annotations

from datetime import datetime

from job_hunter_ai.common.models import NormalizedJobPosting
from job_hunter_ai.connectors.quality import average_field_coverage
from job_hunter_ai.connectors.quality import compute_quality
from job_hunter_ai.connectors.quality import field_coverage
from job_hunter_ai.connectors.quality import ghost_rate
from job_hunter_ai.connectors.quality import is_ghost_or_stale
from job_hunter_ai.connectors.quality import parse_rate


def make_posting(**overrides: object) -> NormalizedJobPosting:
    base = dict(
        posting_id="posting-1",
        source_name="greenhouse",
        source_type="ats",
        external_id="123",
        source_url="https://example.com/jobs/123",
        company_name="Example",
        company_domain="example.com",
        title_raw="Product Manager",
        title_normalized="product manager",
        description_raw="<p>Desc</p>",
        description_text="Desc",
        location_raw="Remote",
        location_country=None,
        location_region=None,
        location_city=None,
        remote_mode="remote",
        employment_type="full-time",
        seniority="senior",
        role_family="product",
        market="saas",
        compensation_min=None,
        compensation_max=None,
        compensation_currency=None,
        posted_at=datetime(2026, 7, 1),
        discovered_at=datetime(2026, 7, 2),
        normalized_at=datetime(2026, 7, 2),
        content_hash="abc",
        parse_status="parsed",
        parse_warnings=[],
    )
    base.update(overrides)
    return NormalizedJobPosting(**base)


def test_parse_rate_returns_zero_when_no_raw_records() -> None:
    assert parse_rate(raw_record_count=0, normalized_postings_count=0) == 0.0


def test_field_coverage_returns_full_weight_for_complete_posting() -> None:
    assert field_coverage(make_posting()) == 1.0


def test_field_coverage_drops_when_weighted_fields_are_missing() -> None:
    posting = make_posting(title_normalized=None, source_url=None)
    assert field_coverage(posting) == 0.7


def test_is_ghost_or_stale_flags_failed_parse_and_warning_markers() -> None:
    assert is_ghost_or_stale(make_posting(parse_status="failed")) is True
    assert is_ghost_or_stale(make_posting(parse_warnings=["ghost"])) is True
    assert is_ghost_or_stale(make_posting(parse_warnings=["stale"])) is True
    assert is_ghost_or_stale(make_posting()) is False


def test_ghost_rate_returns_fraction_of_flagged_postings() -> None:
    postings = [
        make_posting(),
        make_posting(posting_id="posting-2", parse_warnings=["ghost"]),
    ]
    assert ghost_rate(postings) == 0.5


def test_average_field_coverage_returns_zero_for_empty_input() -> None:
    assert average_field_coverage([]) == 0.0


def test_compute_quality_uses_agreed_formula() -> None:
    postings = [
        make_posting(),
        make_posting(posting_id="posting-2", source_url=None, parse_warnings=["ghost"]),
    ]

    quality = compute_quality(raw_record_count=4, postings=postings)

    assert quality.parse_rate == 0.5
    assert quality.field_coverage == 0.95
    assert quality.ghost_rate == 0.5
    assert quality.quality == 0.2375

