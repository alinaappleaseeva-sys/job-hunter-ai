"""Lever ATS connector.

Fetches public job postings from Lever's no-auth Postings API and
emits ``RawSourceRecord`` objects per docs/specs/source-contract.md.

Endpoint:
    GET https://api.lever.co/v0/postings/{site}?mode=json

Notes vs contract:
    - Lever has excellent coverage: title, description, location, remote,
      employment_type (via commitment), posted date, etc.
    - Supports pagination (``skip``/``limit``); boards with more than one page
      are drained automatically.
    - Fields like ``categories.commitment``, ``categories.location``,
      ``descriptionPlain``, ``workplaceType``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.connectors.base import (
    Connector,
    ConnectorEmptyResponseError,
    ConnectorSchemaError,
    DirectClient,
    FetchResult,
    make_content_hash,
    utcnow,
)
from job_hunter_ai.connectors.http_client import HttpxDirectClient

_BASE_URL = "https://api.lever.co/v0/postings"
_SOURCE_TYPE = "ats"
_RECORD_TYPE = "job_posting"
_PROVIDER = "lever"


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse Lever Unix timestamp (ms) or ISO string into tz-aware datetime."""
    if not value:
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000, tz=UTC)
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, OSError, OverflowError):
        return None
    return None


def _hash_payload(payload: dict[str, Any]) -> str | None:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return make_content_hash(canonical)


def _extract_jobs(payload: Any) -> list[dict[str, Any]]:
    """Normalize Lever response into a list of job dicts.

    The live Postings API returns a top-level JSON array. Some integrations
    wrap postings under a ``data`` key, so both shapes are accepted.
    """
    if isinstance(payload, list):
        return [job for job in payload if isinstance(job, dict)]

    if isinstance(payload, dict):
        if "data" in payload:
            jobs = payload.get("data")
            if isinstance(jobs, list):
                return [job for job in jobs if isinstance(job, dict)]
            raise ConnectorSchemaError("Lever 'data' field is not a list")
        raise ConnectorSchemaError("Lever response missing postings list")

    raise ConnectorSchemaError("Lever response is not a JSON array or object")


class LeverConnector(Connector):
    """Connector for a single Lever job board (one company/site).

    Parameters
    ----------
    site:
        Lever site slug, e.g. ``"leverdemo"``.
    client:
        Optional injected client implementing :class:`DirectClient` (for tests).
    page_size:
        Page size for ``skip``/``limit`` pagination (default 100).
    """

    def __init__(
        self,
        site: str,
        *,
        client: DirectClient | None = None,
        page_size: int = 100,
    ) -> None:
        if not site or not site.strip():
            raise ValueError("site must be a non-empty Lever site name (e.g. 'leverdemo')")
        if page_size <= 0:
            raise ValueError("page_size must be positive")
        self._site = site.strip()
        self._client = client
        self._page_size = page_size
        super().__init__(
            source_name=f"lever:{self._site}",
            source_type=_SOURCE_TYPE,
        )

    def _page_url(self, *, skip: int, page_size: int) -> str:
        return f"{_BASE_URL}/{self._site}?mode=json&limit={page_size}&skip={skip}"

    @property
    def url(self) -> str:
        """First-page URL for this Lever site."""
        return self._page_url(skip=0, page_size=self._page_size)

    def fetch(
        self,
        *,
        cursor_value: str | None = None,
        limit: int | None = None,
    ) -> FetchResult:
        """Fetch job postings from Lever, draining paginated pages when needed."""
        skip = int(cursor_value) if cursor_value else 0
        page_size = self._page_size

        client = self._client or HttpxDirectClient()
        owns_client = self._client is None

        all_jobs: list[dict[str, Any]] = []
        pages_fetched = 0
        last_batch: list[dict[str, Any]] = []
        next_skip: int | None = skip

        try:
            while next_skip is not None:
                payload = client.get(self._page_url(skip=next_skip, page_size=page_size))
                last_batch = _extract_jobs(payload)
                pages_fetched += 1

                if not last_batch and next_skip == 0:
                    raise ConnectorEmptyResponseError(
                        f"Lever site '{self._site}' returned zero jobs"
                    )

                all_jobs.extend(last_batch)

                if limit is not None and len(all_jobs) >= limit:
                    all_jobs = all_jobs[:limit]
                    if len(last_batch) == page_size:
                        next_skip = next_skip + len(last_batch)
                    else:
                        next_skip = None
                    break

                if len(last_batch) < page_size:
                    next_skip = None
                else:
                    next_skip += len(last_batch)
        finally:
            if owns_client and hasattr(client, "close"):
                client.close()

        fetched_at = utcnow()
        records = [self._to_record(job, fetched_at=fetched_at) for job in all_jobs]

        cursor_after = str(next_skip) if next_skip is not None else None

        return FetchResult(
            records=records,
            cursor_after=cursor_after,
            run_metadata={
                "provider": _PROVIDER,
                "site": self._site,
                "pages_fetched": pages_fetched,
                "raw_job_count": len(all_jobs),
                "emitted_record_count": len(records),
                "page_size": page_size,
            },
        )

    def _to_record(
        self,
        job: dict[str, Any],
        *,
        fetched_at: datetime,
    ) -> RawSourceRecord:
        external_id = job.get("id")
        source_url = job.get("hostedUrl") or job.get("applyUrl")

        categories = job.get("categories") if isinstance(job.get("categories"), dict) else {}
        location = categories.get("location")
        commitment = categories.get("commitment")
        remote_mode = (
            categories.get("remote")
            or job.get("remote")
            or job.get("workplaceType")
        )

        metadata: dict[str, Any] = {
            "provider": _PROVIDER,
            "fetched_via": "postings_api",
            "cursor_type": "skip",
            "cursor_value": None,
            "http_status": 200,
            "site": self._site,
            "team": categories.get("team"),
            "department": categories.get("department"),
            "location": location,
            "commitment": commitment,
            "employment_type": commitment,
            "remote_mode": remote_mode,
            "workplace_type": job.get("workplaceType"),
            "title": job.get("text"),
        }

        return RawSourceRecord(
            source_name=self.source_name,
            source_type=_SOURCE_TYPE,
            record_type=_RECORD_TYPE,
            external_id=str(external_id) if external_id is not None else None,
            source_url=source_url,
            fetched_at=fetched_at,
            discovered_at=_parse_timestamp(job.get("createdAt")),
            payload=job,
            content_hash=_hash_payload(job),
            cursor_value=None,
            metadata=metadata,
        )