"""Shared helpers for provider mappers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from job_hunter_ai.common.models import NormalizedJobPosting
from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.normalization.fields.enrichment import infer_role_family
from job_hunter_ai.normalization.registry import resolve_provider


def utcnow() -> datetime:
    return datetime.now(UTC)


def parse_iso_timestamp(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def parse_lever_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000, tz=UTC)
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, OSError, OverflowError):
        return None
    return None


def posting_shell(record: RawSourceRecord) -> NormalizedJobPosting:
    """Seed a posting with provenance copied from the raw record."""
    return NormalizedJobPosting(
        posting_id=str(uuid4()),
        source_name=record.source_name,
        source_type=record.source_type,
        external_id=record.external_id,
        source_url=record.source_url,
        company_name=None,
        company_domain=None,
        title_raw=None,
        title_normalized=None,
        description_raw=None,
        description_text=None,
        location_raw=None,
        location_country=None,
        location_region=None,
        location_city=None,
        remote_mode=None,
        employment_type=None,
        seniority=None,
        role_family=None,
        market=None,
        compensation_min=None,
        compensation_max=None,
        compensation_currency=None,
        posted_at=None,
        discovered_at=record.discovered_at,
        normalized_at=utcnow(),
        content_hash=record.content_hash,
        parse_status="partial",
        parse_warnings=[],
    )


def company_name_from_record(record: RawSourceRecord) -> str | None:
    metadata = record.metadata or {}
    if metadata.get("company_name"):
        return str(metadata["company_name"])
    payload = record.payload or {}
    if payload.get("company_name"):
        return str(payload["company_name"])
    source_slug = record.source_name.split(":", 1)[-1]
    provider = resolve_provider(record.source_name)
    if provider in {"lever", "ashby", "greenhouse"} and source_slug:
        return source_slug
    return None


def resolve_role_family(title: str | None, *, department: str | None = None) -> str:
    family = infer_role_family(title, department=department)
    return family or "other"


def multi_location_warning(location_raw: str | None) -> bool:
    if not location_raw or not str(location_raw).strip():
        return False
    text = str(location_raw)
    if ";" in text:
        return True
    parts = [part.strip() for part in text.split(",") if part.strip()]
    return len(parts) >= 3


def finalize_parse_status(
    posting: NormalizedJobPosting,
    warnings: list[str],
) -> tuple[str, list[str]]:
    """Apply parse-status rules from normalization_field_checks rubric."""
    deduped = list(dict.fromkeys(warnings))

    if not posting.title_normalized:
        if "title_missing" not in deduped:
            deduped.insert(0, "title_missing")
        posting.parse_warnings = deduped
        return "failed", deduped

    required = (
        posting.company_name,
        posting.description_text,
        posting.source_url,
    )
    if all(required) and not deduped:
        posting.parse_warnings = []
        return "parsed", []

    posting.parse_warnings = deduped
    return "partial", deduped