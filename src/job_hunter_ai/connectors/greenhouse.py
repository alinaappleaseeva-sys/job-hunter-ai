"""Greenhouse ATS connector.

Fetches public job-board postings from Greenhouse's no-auth Job Board API and
emits ``RawSourceRecord`` objects per docs/specs/source-contract.md.

Endpoint:
    GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true

The Job Board API is public (no authentication — that is only required for the
private Harvest API used to read candidates/applications). The endpoint returns
the ENTIRE board in a single response; ``per_page``/``page`` query params are
ignored (verified live: a 510-job board returns all 510 regardless of paging).
Response shape::

    {"jobs": [ {...}, ... ], "meta": {"total": N}}

Source-field notes vs the contract (docs/specs/source-contract.md §10):
    - ``company`` IS available here (``company_name``) — unlike Ashby.
    - ``employment_type`` is NOT exposed by the Board API, so field_coverage
      will legitimately be lower on that component. This is a real limitation
      of the source, not a parser bug.
    - ``content`` is escaped HTML (the contract's ``description`` proxy).
    - ``location`` is a nested object (``location.name``), not a bare string.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import httpx

from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.connectors.base import (
    Connector,
    ConnectorEmptyResponseError,
    ConnectorNetworkError,
    ConnectorRateLimitError,
    ConnectorSchemaError,
    DirectClient,
    FetchResult,
    make_content_hash,
    utcnow,
)

_BASE_URL = "https://boards-api.greenhouse.io/v1/boards"
_SOURCE_TYPE = "ats"
_RECORD_TYPE = "job_posting"
_PROVIDER = "greenhouse"


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse Greenhouse ISO-8601 timestamps into tz-aware datetimes.

    Greenhouse emits values like ``2026-06-02T08:58:57-04:00``. Returns ``None``
    for missing or unparsable values rather than raising, so one malformed
    timestamp never aborts a whole run.
    """
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _hash_payload(payload: dict[str, Any]) -> str | None:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return make_content_hash(canonical)


class HttpxDirectClient:
    """HTTP client for Greenhouse Job Board API requests."""

    def __init__(self, *, timeout: float = 30.0) -> None:
        self._client = httpx.Client(timeout=timeout)

    def get(self, url: str, **kwargs: Any) -> dict[str, Any]:
        headers = kwargs.get("headers")
        try:
            response = self._client.get(url, headers=headers, follow_redirects=True)
        except httpx.NetworkError as exc:
            raise ConnectorNetworkError(f"Network error reaching {url}: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise ConnectorNetworkError(f"Timeout reaching {url}: {exc}") from exc

        if response.status_code == 429:
            retry_after = response.headers.get("retry-after", "unknown")
            raise ConnectorRateLimitError(
                f"Rate limited by {url} (retry-after={retry_after})"
            )

        response.raise_for_status()

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise ConnectorSchemaError(f"Non-JSON response from {url}: {exc}") from exc

        if not isinstance(payload, dict):
            raise ConnectorSchemaError(f"Expected JSON object from {url}")
        return payload

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> HttpxDirectClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class GreenhouseConnector(Connector):
    """Connector for a single Greenhouse job board (one company).

    Parameters
    ----------
    board_token:
        The Greenhouse board token / slug, e.g. ``"stripe"``. This is the
        ``{board_token}`` path segment of the Job Board API URL.
    client:
        Optional injected client implementing :class:`DirectClient` (for tests).
        A default HTTP client is created lazily when not supplied.
    include_content:
        Whether to request ``content=true`` (full HTML job description).
    """

    def __init__(
        self,
        board_token: str,
        *,
        client: DirectClient | None = None,
        include_content: bool = True,
    ) -> None:
        if not board_token or not board_token.strip():
            raise ValueError("board_token must be a non-empty Greenhouse board slug")
        self._board_token = board_token.strip()
        self._client = client
        self._include_content = include_content
        super().__init__(
            source_name=f"greenhouse:{self._board_token}",
            source_type=_SOURCE_TYPE,
        )

    @property
    def url(self) -> str:
        """Fully-qualified Job Board API URL for this board."""
        url = f"{_BASE_URL}/{self._board_token}/jobs"
        if self._include_content:
            url += "?content=true"
        return url

    def fetch(
        self,
        *,
        cursor_value: str | None = None,
        limit: int | None = None,
    ) -> FetchResult:
        """Fetch the full job board and return one RawSourceRecord per posting.

        Raises
        ------
        ConnectorSchemaError
            If the response is not a JSON object or lacks a ``jobs`` list.
        ConnectorEmptyResponseError
            If the response is well-formed but contains zero jobs.
        ConnectorNetworkError / ConnectorRateLimitError
            Propagated from the HTTP client.
        """
        _ = cursor_value
        _ = limit

        client = self._client or HttpxDirectClient()
        owns_client = self._client is None
        try:
            payload = client.get(self.url)
        finally:
            if owns_client and hasattr(client, "close"):
                client.close()

        if "jobs" not in payload:
            raise ConnectorSchemaError("Greenhouse response missing 'jobs' key")

        jobs = payload.get("jobs")
        if not isinstance(jobs, list):
            raise ConnectorSchemaError("Greenhouse 'jobs' field is not a list")

        if not jobs:
            raise ConnectorEmptyResponseError(
                f"Greenhouse board '{self._board_token}' returned zero jobs"
            )

        fetched_at = utcnow()
        raw_meta = payload.get("meta")
        meta: dict[str, Any] = raw_meta if isinstance(raw_meta, dict) else {}

        records: list[RawSourceRecord] = []
        for job in jobs:
            if not isinstance(job, dict):
                continue
            records.append(self._to_record(job, fetched_at=fetched_at, meta=meta))

        return FetchResult(
            records=records,
            cursor_after=None,
            run_metadata={
                "provider": _PROVIDER,
                "board_token": self._board_token,
                "board_total": meta.get("total"),
                "raw_job_count": len(jobs),
                "emitted_record_count": len(records),
            },
        )

    def _to_record(
        self,
        job: dict[str, Any],
        *,
        fetched_at: datetime,
        meta: dict[str, Any],
    ) -> RawSourceRecord:
        external_id = job.get("id")
        source_url = job.get("absolute_url")

        location = job.get("location")
        location_name = location.get("name") if isinstance(location, dict) else None

        offices = job.get("offices")
        departments = job.get("departments")

        metadata: dict[str, Any] = {
            "provider": _PROVIDER,
            "fetched_via": "job_board_api",
            "cursor_type": "none",
            "cursor_value": None,
            "http_status": 200,
            "board_token": self._board_token,
            "board_total": meta.get("total"),
            "company_name": job.get("company_name"),
            "location_name": location_name,
            "offices": [o.get("name") for o in offices if isinstance(o, dict)]
            if isinstance(offices, list)
            else None,
            "departments": [d.get("name") for d in departments if isinstance(d, dict)]
            if isinstance(departments, list)
            else None,
            "requisition_id": job.get("requisition_id"),
            # Board API does not expose employment type; recorded as a known gap.
            "employment_type": None,
        }

        return RawSourceRecord(
            source_name=self.source_name,
            source_type=_SOURCE_TYPE,
            record_type=_RECORD_TYPE,
            external_id=str(external_id) if external_id is not None else None,
            source_url=source_url,
            fetched_at=fetched_at,
            discovered_at=_parse_timestamp(job.get("first_published"))
            or _parse_timestamp(job.get("updated_at")),
            payload=job,
            content_hash=_hash_payload(job),
            cursor_value=None,
            metadata=metadata,
        )