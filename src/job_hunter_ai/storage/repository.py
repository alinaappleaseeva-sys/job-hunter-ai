"""Storage repository contracts for the ingestion → normalization pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

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


class JobStorageRepository(Protocol):
    """Backend-agnostic persistence for raw records and normalized postings.

    Maps to ``docs/specs/storage-model.md`` tables:
    - ``raw_source_records`` (§4.4)
    - ``normalized_job_postings`` (§4.5)

    Canonical job persistence is added in Phase 5 (``dedup/``).
    """

    def save_raw(self, record: RawSourceRecord) -> str:
        """Persist a raw record. Returns ``raw_record_id``."""

    def get_raw(self, raw_record_id: str) -> StoredRawRecord | None:
        """Load a raw record by id."""

    def list_raw_by_source(self, source_name: str) -> list[StoredRawRecord]:
        """Return all raw records for a connector source name."""

    def save_normalized(
        self,
        posting: NormalizedJobPosting,
        *,
        raw_record_id: str,
    ) -> str:
        """Persist a normalized posting linked to a raw record. Returns ``posting_id``."""

    def get_normalized(self, posting_id: str) -> StoredNormalizedPosting | None:
        """Load a normalized posting and its lineage."""

    def list_normalized_by_source(self, source_name: str) -> list[StoredNormalizedPosting]:
        """Return all normalized postings for a source."""

    def list_unlinked_raw(self) -> list[StoredRawRecord]:
        """Return raw records that have no normalized posting yet."""