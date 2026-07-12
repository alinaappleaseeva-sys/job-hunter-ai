"""In-memory implementation of :class:`JobStorageRepository`."""

from __future__ import annotations

from uuid import uuid4

from job_hunter_ai.common.models import NormalizedJobPosting
from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.storage.repository import StoredNormalizedPosting
from job_hunter_ai.storage.repository import StoredRawRecord


class MemoryJobStorage:
    """Thread-unsafe in-memory store for tests and local smoke runs."""

    def __init__(self) -> None:
        self._raw: dict[str, StoredRawRecord] = {}
        self._normalized: dict[str, StoredNormalizedPosting] = {}
        self._raw_to_posting: dict[str, str] = {}

    def save_raw(self, record: RawSourceRecord) -> str:
        raw_record_id = str(uuid4())
        stored = StoredRawRecord(raw_record_id=raw_record_id, record=record)
        self._raw[raw_record_id] = stored
        return raw_record_id

    def get_raw(self, raw_record_id: str) -> StoredRawRecord | None:
        return self._raw.get(raw_record_id)

    def list_raw_by_source(self, source_name: str) -> list[StoredRawRecord]:
        return [
            stored
            for stored in self._raw.values()
            if stored.record.source_name == source_name
        ]

    def save_normalized(
        self,
        posting: NormalizedJobPosting,
        *,
        raw_record_id: str,
    ) -> str:
        if raw_record_id not in self._raw:
            raise KeyError(f"Unknown raw_record_id: {raw_record_id}")

        posting_id = posting.posting_id or str(uuid4())
        linked = StoredNormalizedPosting(
            posting_id=posting_id,
            raw_record_id=raw_record_id,
            posting=posting,
        )
        self._normalized[posting_id] = linked
        self._raw_to_posting[raw_record_id] = posting_id
        return posting_id

    def get_normalized(self, posting_id: str) -> StoredNormalizedPosting | None:
        return self._normalized.get(posting_id)

    def list_normalized_by_source(self, source_name: str) -> list[StoredNormalizedPosting]:
        return [
            stored
            for stored in self._normalized.values()
            if stored.posting.source_name == source_name
        ]

    def list_unlinked_raw(self) -> list[StoredRawRecord]:
        return [
            stored
            for raw_id, stored in self._raw.items()
            if raw_id not in self._raw_to_posting
        ]

    def clear(self) -> None:
        """Reset all data — test helper only."""
        self._raw.clear()
        self._normalized.clear()
        self._raw_to_posting.clear()