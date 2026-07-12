"""Normalization pipeline entrypoint."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

from job_hunter_ai.common.models import NormalizedJobPosting
from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.normalization.registry import get_mapper
from job_hunter_ai.normalization.registry import resolve_provider
from job_hunter_ai.normalization.types import NormalizationItemResult
from job_hunter_ai.normalization.types import NormalizationRunResult
from job_hunter_ai.normalization.types import ParseDiagnostics
from job_hunter_ai.storage.repository import JobStorageRepository

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _empty_posting_shell(record: RawSourceRecord) -> NormalizedJobPosting:
    """Minimal posting scaffold copied from raw provenance fields."""
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
        normalized_at=_utcnow(),
        content_hash=record.content_hash,
        parse_status="failed",
        parse_warnings=[],
    )


def _failed_posting(
    record: RawSourceRecord,
    *,
    provider: str | None,
    mapper_name: str | None,
    warnings: list[str],
    error_type: str | None = None,
    error_message: str | None = None,
) -> tuple[NormalizedJobPosting, ParseDiagnostics]:
    posting = _empty_posting_shell(record)
    posting.parse_status = "failed"
    posting.parse_warnings = list(warnings)
    diagnostics = ParseDiagnostics(
        provider=provider,
        mapper_name=mapper_name,
        warnings=list(warnings),
        error_type=error_type,
        error_message=error_message,
    )
    return posting, diagnostics


def normalize_record(
    record: RawSourceRecord,
    *,
    store: JobStorageRepository | None = None,
) -> NormalizationItemResult:
    """Normalize one raw record, optionally persisting raw + normalized rows."""
    provider = resolve_provider(record.source_name)
    raw_record_id: str | None = None
    posting_id: str | None = None
    persisted = False

    if store is not None:
        raw_record_id = store.save_raw(record)

    mapper = get_mapper(record.source_name)
    if mapper is None:
        logger.info(
            "No mapper registered for provider=%s source=%s",
            provider,
            record.source_name,
        )
        posting, diagnostics = _failed_posting(
            record,
            provider=provider,
            mapper_name=None,
            warnings=["unsupported_provider"],
        )
    else:
        try:
            posting = mapper.normalize(record)
            posting.normalized_at = posting.normalized_at or _utcnow()
            if not posting.posting_id:
                posting.posting_id = str(uuid4())
            diagnostics = ParseDiagnostics(
                provider=provider,
                mapper_name=type(mapper).__name__,
                warnings=list(posting.parse_warnings),
            )
        except Exception as exc:  # pragma: no cover - logged and surfaced
            logger.exception(
                "Mapper failed for provider=%s source=%s",
                provider,
                record.source_name,
            )
            posting, diagnostics = _failed_posting(
                record,
                provider=provider,
                mapper_name=type(mapper).__name__,
                warnings=["mapper_error"],
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

    if store is not None and raw_record_id is not None:
        posting_id = store.save_normalized(posting, raw_record_id=raw_record_id)
        persisted = True

    return NormalizationItemResult(
        raw_record_id=raw_record_id,
        posting_id=posting_id,
        posting=posting,
        diagnostics=diagnostics,
        persisted=persisted,
    )


def normalize_postings(
    records: Sequence[RawSourceRecord],
    *,
    store: JobStorageRepository | None = None,
) -> NormalizationRunResult:
    """Normalize a batch of raw records.

    Parameters
    ----------
    records:
        Raw connector output to normalize.
    store:
        Optional repository; when provided, each record is persisted before
        normalization and the resulting posting is saved with lineage.
    """
    items: list[NormalizationItemResult] = []
    parsed = partial = failed = 0

    for record in records:
        item = normalize_record(record, store=store)
        items.append(item)
        status = item.posting.parse_status
        if status == "parsed":
            parsed += 1
        elif status == "partial":
            partial += 1
        else:
            failed += 1

    result = NormalizationRunResult(
        total=len(records),
        parsed=parsed,
        partial=partial,
        failed=failed,
        items=items,
    )
    logger.info(
        "Normalization run complete total=%s parsed=%s partial=%s failed=%s parse_rate=%.2f",
        result.total,
        result.parsed,
        result.partial,
        result.failed,
        result.parse_rate,
    )
    return result