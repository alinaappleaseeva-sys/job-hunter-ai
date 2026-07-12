"""Ashby ATS connector.

Fetches public job-board postings from Ashby's no-auth posting API and emits
``RawSourceRecord`` objects per docs/specs/source-contract.md.

Endpoint:
    GET https://api.ashbyhq.com/posting-api/job-board/{client_name}?includeCompensation=true

Response shape::

    {"jobs": [ {...}, ... ], "apiVersion": "1"}

No server-side pagination is available — a run fetches the full board in one
request. Incremental behaviour is emulated downstream via ``content_hash`` and
``discovered_at`` (``publishedAt``).

Rate-limit guidance (Tier 2 source)
------------------------------------
Ashby's public posting API is **rate-limited**. Naive polling across many boards
will hit HTTP 429 quickly. This connector is intentionally conservative:

- **one HTTP request per ``fetch()``** — no internal retry loop;
- **no parallel requests** — the scheduler must serialize Ashby runs;
- **429 surfaces as** :class:`ConnectorRateLimitError` with ``retry-after`` in
  the message — backoff and retry belong in the ingestion scheduler, not here;
- **prefer longer poll intervals** per board (implementation-plan.md treats
  Ashby as second-wave / Tier 2 for this reason).

Source-field notes vs the contract:
    - No explicit ``company`` field on a single-board response; ``client_name``
      (board slug) is the company proxy in metadata.
    - Rich coverage otherwise: ``employmentType``, ``workplaceType``,
      ``descriptionPlain``/``descriptionHtml``, ``location``,
      ``secondaryLocations``, compensation when ``includeCompensation=true``.
"""

from __future__ import annotations

import json
from datetime import datetime
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
from job_hunter_ai.connectors.http_client import DEFAULT_TIMEOUT
from job_hunter_ai.connectors.http_client import HttpxDirectClient

_BASE_URL = "https://api.ashbyhq.com/posting-api/job-board"
_SOURCE_TYPE = "ats"
_RECORD_TYPE = "job_posting"
_PROVIDER = "ashby"


def _parse_published_at(value: Any) -> datetime | None:
    """Parse Ashby ISO-8601 ``publishedAt`` into a tz-aware datetime."""
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _hash_payload(payload: dict[str, Any]) -> str | None:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return make_content_hash(canonical)


def _remote_mode(job: dict[str, Any]) -> str | bool | None:
    workplace = job.get("workplaceType")
    if workplace:
        return workplace
    if job.get("isRemote") is True:
        return "Remote"
    if job.get("isRemote") is False:
        return "OnSite"
    return None


class AshbyConnector(Connector):
    """Connector for a single Ashby job board (one client/company).

    Parameters
    ----------
    client_name:
        Ashby job-board slug, e.g. ``"Ashby"`` or ``"lido"``.
    client:
        Optional injected client implementing :class:`DirectClient` (for tests).
    include_compensation:
        Whether to append ``includeCompensation=true`` to the request URL.
    request_timeout:
        HTTP timeout in seconds for the single board fetch.
    """

    def __init__(
        self,
        client_name: str,
        *,
        client: DirectClient | None = None,
        include_compensation: bool = True,
        request_timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        if not client_name or not client_name.strip():
            raise ValueError("client_name must be a non-empty Ashby board slug")
        if request_timeout <= 0:
            raise ValueError("request_timeout must be positive")
        self._client_name = client_name.strip()
        self._client = client
        self._include_compensation = include_compensation
        self._request_timeout = request_timeout
        super().__init__(
            source_name=f"ashby:{self._client_name}",
            source_type=_SOURCE_TYPE,
        )

    @property
    def url(self) -> str:
        """Fully-qualified posting-API URL for this board."""
        url = f"{_BASE_URL}/{self._client_name}"
        if self._include_compensation:
            url += "?includeCompensation=true"
        return url

    def fetch(
        self,
        *,
        cursor_value: str | None = None,
        limit: int | None = None,
    ) -> FetchResult:
        """Fetch the full job board and return one RawSourceRecord per posting."""
        _ = cursor_value

        client = self._client or HttpxDirectClient(timeout=self._request_timeout)
        owns_client = self._client is None

        try:
            payload = client.get(self.url)
        finally:
            if owns_client and hasattr(client, "close"):
                client.close()

        if not isinstance(payload, dict):
            raise ConnectorSchemaError(f"Expected JSON object from {self.url}")

        if "jobs" not in payload:
            raise ConnectorSchemaError("Ashby response missing 'jobs' key")

        jobs = payload.get("jobs")
        if not isinstance(jobs, list):
            raise ConnectorSchemaError("Ashby 'jobs' field is not a list")

        if not jobs:
            raise ConnectorEmptyResponseError(
                f"Ashby board '{self._client_name}' returned zero jobs"
            )

        fetched_at = utcnow()
        api_version = payload.get("apiVersion")

        records: list[RawSourceRecord] = []
        for job in jobs:
            if not isinstance(job, dict):
                continue
            records.append(
                self._to_record(job, fetched_at=fetched_at, api_version=api_version)
            )

        if limit is not None:
            records = records[:limit]

        return FetchResult(
            records=records,
            cursor_after=None,
            run_metadata={
                "provider": _PROVIDER,
                "client_name": self._client_name,
                "api_version": api_version,
                "raw_job_count": len(jobs),
                "emitted_record_count": len(records),
                "include_compensation": self._include_compensation,
                "rate_limit_tier": "tier_2",
            },
        )

    def _to_record(
        self,
        job: dict[str, Any],
        *,
        fetched_at: datetime,
        api_version: Any,
    ) -> RawSourceRecord:
        external_id = job.get("id")
        source_url = job.get("jobUrl") or job.get("applyUrl")
        compensation = job.get("compensation")
        has_compensation = bool(compensation) and compensation != {}
        location = job.get("location")
        secondary_locations = job.get("secondaryLocations")
        remote_mode = _remote_mode(job)

        metadata: dict[str, Any] = {
            "provider": _PROVIDER,
            "fetched_via": "posting_api",
            "cursor_type": "none",
            "cursor_value": None,
            "http_status": 200,
            "client_name": self._client_name,
            "api_version": api_version,
            "title": job.get("title"),
            "department": job.get("department"),
            "team": job.get("team"),
            "location": location,
            "location_name": location,
            "secondary_locations": secondary_locations,
            "employment_type": job.get("employmentType"),
            "workplace_type": job.get("workplaceType"),
            "remote_mode": remote_mode,
            "is_remote": job.get("isRemote"),
            "is_listed": job.get("isListed"),
            "has_compensation": has_compensation,
            "company_name": self._client_name,
        }

        return RawSourceRecord(
            source_name=self.source_name,
            source_type=_SOURCE_TYPE,
            record_type=_RECORD_TYPE,
            external_id=str(external_id) if external_id is not None else None,
            source_url=source_url,
            fetched_at=fetched_at,
            discovered_at=_parse_published_at(job.get("publishedAt")),
            payload=job,
            content_hash=_hash_payload(job),
            cursor_value=None,
            metadata=metadata,
        )