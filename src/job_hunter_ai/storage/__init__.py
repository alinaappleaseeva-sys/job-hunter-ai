"""Persistence layer for raw records, normalized postings, and (later) canonical jobs."""

from job_hunter_ai.storage.memory import MemoryJobStorage
from job_hunter_ai.storage.repository import JobStorageRepository
from job_hunter_ai.storage.repository import StoredNormalizedPosting
from job_hunter_ai.storage.repository import StoredRawRecord

__all__ = [
    "JobStorageRepository",
    "MemoryJobStorage",
    "StoredNormalizedPosting",
    "StoredRawRecord",
]