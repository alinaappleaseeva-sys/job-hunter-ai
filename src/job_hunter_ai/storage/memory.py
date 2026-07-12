"""In-memory implementation of :class:`JobStorageRepository` (incl. Phase 5 canonical support)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from job_hunter_ai.common.models import CanonicalJob
from job_hunter_ai.common.models import CanonicalMergeEvent
from job_hunter_ai.common.models import NormalizedJobPosting
from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.storage.repository import JobStorageRepository
from job_hunter_ai.storage.repository import StoredCanonicalJob
from job_hunter_ai.storage.repository import StoredCanonicalLink
from job_hunter_ai.storage.repository import StoredNormalizedPosting
from job_hunter_ai.storage.repository import StoredRawRecord


class MemoryJobStorage:
    """Thread-unsafe in-memory store for tests and local smoke runs.

    Supports raw, normalized, and (Phase 5) canonical + links + merge events.
    """

    def __init__(self) -> None:
        self._raw: dict[str, StoredRawRecord] = {}
        self._normalized: dict[str, StoredNormalizedPosting] = {}
        self._raw_to_posting: dict[str, str] = {}

        # Phase 5 dedup structures
        self._canonicals: dict[str, StoredCanonicalJob] = {}
        self._links: dict[str, list[str]] = {}  # canonical_id -> posting_ids
        self._posting_to_canonical: dict[str, str] = {}  # posting_id -> canonical_id
        self._merge_events: dict[str, list[CanonicalMergeEvent]] = {}  # canonical_id -> events

    # --- Raw / Normalized (Phase 0-4) ---

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

    # --- Phase 5: Canonical + links + events ---

    def save_canonical(self, canonical: CanonicalJob) -> str:
        cid = canonical.canonical_job_id
        if not cid:
            cid = str(uuid4())
        stored = StoredCanonicalJob(canonical_job_id=cid, canonical=canonical)
        self._canonicals[cid] = stored
        if cid not in self._links:
            self._links[cid] = []
        if cid not in self._merge_events:
            self._merge_events[cid] = []
        return cid

    def get_canonical(self, canonical_job_id: str) -> StoredCanonicalJob | None:
        return self._canonicals.get(canonical_job_id)

    def list_canonicals(self) -> list[StoredCanonicalJob]:
        return list(self._canonicals.values())

    def link_posting_to_canonical(
        self, *, canonical_job_id: str, posting_id: str
    ) -> None:
        if canonical_job_id not in self._canonicals:
            raise KeyError(f"Unknown canonical_job_id: {canonical_job_id}")
        if posting_id not in self._links.get(canonical_job_id, []):
            self._links.setdefault(canonical_job_id, []).append(posting_id)
        self._posting_to_canonical[posting_id] = canonical_job_id

    def list_postings_for_canonical(
        self, canonical_job_id: str
    ) -> list[StoredNormalizedPosting]:
        if canonical_job_id not in self._links:
            return []
        posting_ids = self._links[canonical_job_id]
        return [
            self._normalized[pid]
            for pid in posting_ids
            if pid in self._normalized
        ]

    def save_merge_event(self, event: CanonicalMergeEvent) -> str:
        cid = event.canonical_job_id
        if cid not in self._merge_events:
            self._merge_events[cid] = []
        self._merge_events[cid].append(event)
        # synthetic id = count based
        return f"{cid}:{len(self._merge_events[cid])}"

    def list_merge_events_for_canonical(
        self, canonical_job_id: str
    ) -> list[CanonicalMergeEvent]:
        return list(self._merge_events.get(canonical_job_id, []))

    # --- helpers ---

    def clear(self) -> None:
        """Reset all data — test helper only."""
        self._raw.clear()
        self._normalized.clear()
        self._raw_to_posting.clear()
        self._canonicals.clear()
        self._links.clear()
        self._posting_to_canonical.clear()
        self._merge_events.clear()

    def get_canonical_for_posting(self, posting_id: str) -> str | None:
        """Test helper."""
        return self._posting_to_canonical.get(posting_id)
