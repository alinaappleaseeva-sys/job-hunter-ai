"""Remote OK job board connector (Phase 8).

Public API: https://remoteok.com/api
Returns JSON list of remote jobs.

Fits job board family (non-ATS). Strong for remote roles.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.connectors.base import (
    Connector,
    ConnectorEmptyResponseError,
    ConnectorSchemaError,
    FetchResult,
    make_content_hash,
    utcnow,
)
from job_hunter_ai.connectors.http_client import HttpxDirectClient

_BASE_URL = "https://remoteok.com/api"
_SOURCE_TYPE = "job_board"
_RECORD_TYPE = "job_posting"
_PROVIDER = "remoteok"


class RemoteOKConnector(Connector):
    """Remote OK connector.

    Fetches full list (no pagination in public API for MVP).
    Emits RawSourceRecord.
    """

    def __init__(self, source_name: str = "remoteok", client: Any | None = None) -> None:
        super().__init__(source_name, _SOURCE_TYPE)
        self.client = client or HttpxDirectClient()

    def fetch(self, *, cursor_value: str | None = None, limit: int | None = None) -> FetchResult:
        try:
            resp = self.client.get(_BASE_URL, timeout=30)
            data = resp.json() if hasattr(resp, "json") else resp
        except Exception as exc:
            raise ConnectorSchemaError(f"RemoteOK fetch failed: {exc}") from exc

        if not isinstance(data, list):
            raise ConnectorSchemaError("RemoteOK expected list at root")

        records: list[RawSourceRecord] = []
        now = utcnow()

        for item in data:
            if not isinstance(item, dict):
                continue
            if "id" not in item or not item.get("position"):
                continue  # skip non-job entries (sometimes headers)

            external_id = str(item.get("id"))
            url = item.get("url") or f"https://remoteok.com/remote-jobs/{external_id}"
            title = item.get("position")
            company = item.get("company")
            location = item.get("location")
            description = item.get("description") or item.get("tags", "")
            posted = item.get("date")  # e.g. "2026-07-10T..."

            payload = {
                "id": external_id,
                "position": title,
                "company": company,
                "location": location,
                "url": url,
                "description": description,
                "date": posted,
                "tags": item.get("tags"),
                "salary": item.get("salary"),
            }

            content_hash = make_content_hash(str(payload))

            record = RawSourceRecord(
                source_name=self.source_name,
                source_type=self.source_type,
                record_type=_RECORD_TYPE,
                external_id=external_id,
                source_url=url,
                fetched_at=now,
                discovered_at=self._parse_date(posted),
                payload=payload,
                content_hash=content_hash,
                cursor_value=cursor_value,
                metadata={"provider": _PROVIDER, "tags": item.get("tags")},
            )
            records.append(record)

            if limit and len(records) >= limit:
                break

        if not records:
            raise ConnectorEmptyResponseError("RemoteOK returned no usable jobs")

        return FetchResult(records=records, cursor_after=str(now))

    def _parse_date(self, value: Any) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None
