"""Storage repository contracts for the ingestion → normalization → dedup pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from job_hunter_ai.common.models import CanonicalJob
from job_hunter_ai.common.models import CanonicalMergeEvent
from job_hunter_ai.common.models import NormalizedJobPosting
from job_hunter_ai.common.models import RawSourceRecord


@dataclass(slots=True)
class StoredRawRecord:
    """A persisted raw source record with storage-layer identity."""

    raw_record_id: str
    record: RawSourceRecord


@dataclass(slots=True)
class StoredNormalizedPosting:
    """A persisted normalized posting linked to its source raw record."""

    posting_id: str
    raw_record_id: str
    posting: NormalizedJobPosting


@dataclass(slots=True)
class StoredCanonicalJob:
    """A persisted canonical job (Phase 5)."""

    canonical_job_id: str
    canonical: CanonicalJob


@dataclass(slots=True)
class StoredCanonicalLink:
    """A link between a canonical job and a normalized posting."""

    canonical_job_id: str
    posting_id: str
    linked_at: datetime


class JobStorageRepository(Protocol):
    """Backend-agnostic persistence for raw records, normalized postings, and canonical jobs.

    Maps to ``docs/specs/storage-model.md`` tables (core layers + dedup §4.6-4.8).
    """

    def save_raw(self, record: RawSourceRecord) -> str:
        """Persist a raw record. Returns ``raw_record_id``."""
        ...

    def get_raw(self, raw_record_id: str) -> StoredRawRecord | None:
        """Load a raw record by id."""
        ...

    def list_raw_by_source(self, source_name: str) -> list[StoredRawRecord]:
        """Return all raw records for a connector source name."""
        ...

    def save_normalized(
        self,
        posting: NormalizedJobPosting,
        *,
        raw_record_id: str,
    ) -> str:
        """Persist a normalized posting linked to a raw record. Returns ``posting_id``."""
        ...

    def get_normalized(self, posting_id: str) -> StoredNormalizedPosting | None:
        """Load a normalized posting and its lineage."""
        ...

    def list_normalized_by_source(self, source_name: str) -> list[StoredNormalizedPosting]:
        """Return all normalized postings for a source."""
        ...

    def list_unlinked_raw(self) -> list[StoredRawRecord]:
        """Return raw records that have no normalized posting yet."""
        ...

    # --- Phase 5: Canonical / Dedup support ---

    def save_canonical(self, canonical: CanonicalJob) -> str:
        """Persist (or upsert) a canonical job. Returns ``canonical_job_id``."""
        ...

    def get_canonical(self, canonical_job_id: str) -> StoredCanonicalJob | None:
        """Load a canonical job by id."""
        ...

    def list_canonicals(self) -> list[StoredCanonicalJob]:
        """Return all canonical jobs (for smoke / tests)."""
        ...

    def link_posting_to_canonical(
        self, *, canonical_job_id: str, posting_id: str
    ) -> None:
        """Create / ensure a link from posting to its canonical job.

        Idempotent for MVP.
        """
        ...

    def list_postings_for_canonical(
        self, canonical_job_id: str
    ) -> list[StoredNormalizedPosting]:
        """Return the normalized postings linked to this canonical."""
        ...

    def save_merge_event(self, event: CanonicalMergeEvent) -> str:
        """Persist a dedup merge audit event. Returns a synthetic id."""
        ...

    def list_merge_events_for_canonical(
        self, canonical_job_id: str
    ) -> list[CanonicalMergeEvent]:
        """Return merge events for a given canonical (for audit / evals)."""
        ...
