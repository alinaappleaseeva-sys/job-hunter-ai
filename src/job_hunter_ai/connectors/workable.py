"""Workable ATS connector (Wave 1).

Workable exposes public job data without auth for many companies.

Common endpoints:
- https://www.workable.com/api/accounts/{subdomain}
- https://apply.workable.com/api/v3/accounts/{subdomain}/jobs (more complete in some cases)

The connector takes a subdomain (e.g. "acme" for acme.workable.com or apply.workable.com/acme).

Usage:
    conn = WorkableConnector(subdomain="example")
    result = conn.fetch(limit=20)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.connectors.base import (
    Connector,
    ConnectorNetworkError,
    ConnectorSchemaError,
    FetchResult,
    make_content_hash,
    utcnow,
)


class WorkableConnector(Connector):
    """Workable public jobs connector."""

    def __init__(self, subdomain: str, source_name: str | None = None) -> None:
        name = source_name or f"workable:{subdomain}"
        super().__init__(name, "ats")
        self.subdomain = subdomain

    def _get_jobs_url(self) -> str:
        # Primary public endpoint (works for many boards)
        return f"https://www.workable.com/api/accounts/{self.subdomain}"

    def fetch(self, *, cursor_value: str | None = None, limit: int | None = None) -> FetchResult:
        now = utcnow()
        url = self._get_jobs_url()

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise ConnectorNetworkError(f"Workable network error for {self.subdomain}: {exc}") from exc
        except Exception as exc:
            raise ConnectorSchemaError(f"Workable fetch failed for {self.subdomain}: {exc}") from exc

        jobs = []
        # Response shape can vary; try common paths
        if isinstance(data, dict):
            if "jobs" in data:
                jobs = data["jobs"]
            elif "results" in data:
                jobs = data["results"]
            else:
                # Sometimes the top level has account info + jobs under another key
                for key in ("published_jobs", "open_jobs", "jobs"):
                    if key in data and isinstance(data[key], list):
                        jobs = data[key]
                        break

        records: list[RawSourceRecord] = []

        for idx, job in enumerate(jobs):
            if not isinstance(job, dict):
                continue

            title = job.get("title") or job.get("name") or ""
            if not title:
                continue

            job_id = str(job.get("id") or job.get("shortcode") or idx)
            # Build a usable apply URL
            apply_url = job.get("application_url") or job.get("url")
            if not apply_url:
                apply_url = f"https://apply.workable.com/{self.subdomain}/j/{job_id}"

            payload = {
                "title": title,
                "id": job_id,
                "company": job.get("company_name") or job.get("company"),
                "location": job.get("location") or job.get("city"),
                "remote": job.get("remote") or job.get("workplace_type"),
                "employment_type": job.get("employment_type") or job.get("type"),
                "url": apply_url,
                "description": (job.get("description") or "")[:800],
                "compensation": job.get("salary") or job.get("compensation"),
            }

            record = RawSourceRecord(
                source_name=self.source_name,
                source_type=self.source_type,
                record_type="job_posting",
                external_id=job_id,
                source_url=apply_url,
                fetched_at=now,
                discovered_at=self._parse_date(job.get("created_at") or job.get("published_at")),
                payload=payload,
                content_hash=make_content_hash(title + "|" + apply_url),
                cursor_value=cursor_value,
                metadata={"provider": "workable", "subdomain": self.subdomain},
            )
            records.append(record)

            if limit and len(records) >= limit:
                break

        return FetchResult(records=records, cursor_after=str(now))

    def _parse_date(self, value: Any) -> datetime | None:
        if not value:
            return None
        try:
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(value / 1000)
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None


def load_sample_workable_jobs() -> list[dict]:
    """Sample data for tests / offline."""
    return [
        {
            "id": "wf-123",
            "title": "Head of Operations",
            "company_name": "Acme Labs",
            "location": "Remote",
            "remote": True,
            "application_url": "https://apply.workable.com/acme/j/123",
        },
        {
            "id": "wf-456",
            "title": "Program Manager - Web3",
            "company_name": "DAO Co",
            "location": "Remote",
            "remote": True,
            "application_url": "https://apply.workable.com/acme/j/456",
        },
    ]
