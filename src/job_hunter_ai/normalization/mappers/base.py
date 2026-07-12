"""Base mapper contract for provider-specific normalization."""

from __future__ import annotations

from abc import ABC, abstractmethod

from job_hunter_ai.common.models import NormalizedJobPosting
from job_hunter_ai.common.models import RawSourceRecord


class BaseMapper(ABC):
    """Normalize one ``RawSourceRecord`` into a ``NormalizedJobPosting``."""

    provider: str

    @abstractmethod
    def normalize(self, record: RawSourceRecord) -> NormalizedJobPosting:
        """Map source-native payload fields into the shared posting schema."""