"""Persistence layer for raw records, normalized postings, and canonical jobs."""

from job_hunter_ai.storage.memory import MemoryJobStorage
from job_hunter_ai.storage.repository import JobStorageRepository
from job_hunter_ai.storage.repository import StoredCanonicalJob
from job_hunter_ai.storage.repository import StoredCanonicalLink
from job_hunter_ai.storage.repository import StoredNormalizedPosting
from job_hunter_ai.storage.repository import StoredRawRecord

__all__ = [
    "JobStorageRepository",
    "MemoryJobStorage",
    "StoredCanonicalJob",
    "StoredCanonicalLink",
    "StoredNormalizedPosting",
    "StoredRawRecord",
]
