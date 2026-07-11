"""Base contracts and helpers for source connectors.

The goal of this module is to give every connector one shared execution
surface without forcing source-specific behavior into the common layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from typing import Any, Protocol

from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.common.models import SourceRunResult


JsonDict = dict[str, Any]


class ConnectorError(Exception):
    """Base exception for connector failures."""


class ConnectorNetworkError(ConnectorError):
    """Raised when the connector cannot reliably reach the source."""


class ConnectorAuthError(ConnectorError):
    """Raised when the connector lacks valid credentials or access."""


class ConnectorRateLimitError(ConnectorError):
    """Raised when the source rejects the connector due to rate limiting."""


class ConnectorSchemaError(ConnectorError):
    """Raised when source structure changes or cannot be parsed safely."""


class ConnectorEmptyResponseError(ConnectorError):
    """Raised when the source responds successfully but with no useful content."""


class ConnectorPartialFetchError(ConnectorError):
    """Raised when the connector fetches only part of the expected result set."""


class DirectClient(Protocol):
    """Minimal client protocol for direct connector dependencies.

    This keeps the first connector implementations flexible: tests can inject a
    fake client while production code can use a small HTTP wrapper or SDK.
    """

    def get(self, url: str, **kwargs: Any) -> Any:
        """Perform a GET request and return a client-specific response object."""


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)


def make_content_hash(value: str | bytes | None) -> str | None:
    """Create a stable SHA-256 hash for source content.

    Returns ``None`` for missing or empty values.
    """

    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip().encode("utf-8")
    if not value:
        return None
    return hashlib.sha256(value).hexdigest()


@dataclass(slots=True)
class FetchResult:
    """Container for one connector execution outcome before persistence."""

    records: list[RawSourceRecord]
    cursor_after: str | None = None
    run_metadata: JsonDict | None = None


class Connector(ABC):
    """Abstract base class for all source connectors."""

    source_name: str
    source_type: str

    def __init__(self, source_name: str, source_type: str) -> None:
        self.source_name = source_name
        self.source_type = source_type

    @abstractmethod
    def fetch(
        self,
        *,
        cursor_value: str | None = None,
        limit: int | None = None,
    ) -> FetchResult:
        """Fetch raw records from the source.

        Implementations should return source-native records already transformed
        into ``RawSourceRecord`` objects.
        """

    def run(
        self,
        *,
        cursor_value: str | None = None,
        limit: int | None = None,
    ) -> tuple[FetchResult, SourceRunResult]:
        """Run the connector and produce both records and run telemetry."""

        started_at = utcnow()
        try:
            fetch_result = self.fetch(cursor_value=cursor_value, limit=limit)
            finished_at = utcnow()
            run_result = SourceRunResult(
                source_name=self.source_name,
                started_at=started_at,
                finished_at=finished_at,
                success=True,
                records_fetched=len(fetch_result.records),
                records_emitted=len(fetch_result.records),
                records_persisted=0,
                cursor_before=cursor_value,
                cursor_after=fetch_result.cursor_after,
                run_metadata=fetch_result.run_metadata or {},
            )
            return fetch_result, run_result
        except ConnectorError as exc:
            finished_at = utcnow()
            run_result = SourceRunResult(
                source_name=self.source_name,
                started_at=started_at,
                finished_at=finished_at,
                success=False,
                records_fetched=0,
                records_emitted=0,
                records_persisted=0,
                cursor_before=cursor_value,
                cursor_after=cursor_value,
                error_type=type(exc).__name__,
                error_message=str(exc),
                run_metadata={},
            )
            raise

