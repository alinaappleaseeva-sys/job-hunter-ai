"""Wellfound (formerly AngelList) connector (Phase 8 stub).

Wellfound jobs are heavily client-side rendered.
For MVP we use pre-fetched sample data / fixtures.
Real implementation can use Getro-like API or scraping later.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.connectors.base import (
    Connector,
    ConnectorEmptyResponseError,
    FetchResult,
    make_content_hash,
    utcnow,
)


class WellfoundConnector(Connector):
    """Wellfound connector (MVP stub version).

    source_name example: "wellfound"
    """

    def __init__(self, source_name: str = "wellfound", jobs: list[dict] | None = None) -> None:
        super().__init__(source_name, "job_board")
        self.jobs = jobs or []

    def fetch(self, *, cursor_value: str | None = None, limit: int | None = None) -> FetchResult:
        now = utcnow()
        records: list[RawSourceRecord] = []

        for idx, job in enumerate(self.jobs):
            if not isinstance(job, dict):
                continue

            title = job.get("title") or job.get("position")
            company = job.get("company")
            if not title:
                continue

            external_id = str(job.get("id", idx))
            url = job.get("url") or f"https://wellfound.com/jobs/{external_id}"

            payload = {
                "id": external_id,
                "title": title,
                "company": company,
                "location": job.get("location"),
                "url": url,
                "description": job.get("description"),
                "compensation": job.get("compensation"),
                "equity": job.get("equity"),
                "remote": job.get("remote"),
            }

            record = RawSourceRecord(
                source_name=self.source_name,
                source_type=self.source_type,
                record_type="job_posting",
                external_id=external_id,
                source_url=url,
                fetched_at=now,
                discovered_at=self._parse_date(job.get("posted")),
                payload=payload,
                content_hash=make_content_hash(str(payload)),
                cursor_value=cursor_value,
                metadata={"provider": "wellfound"},
            )
            records.append(record)

            if limit and len(records) >= limit:
                break

        if not records and self.jobs:
            raise ConnectorEmptyResponseError("No usable Wellfound jobs in sample")

        return FetchResult(records=records, cursor_after=str(now))

    def _parse_date(self, value: Any) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None


def load_sample_wellfound_jobs() -> list[dict]:
    """Sample jobs for tests (Phase 8)."""
    return [
        {
            "id": "wf-1001",
            "title": "Senior Software Engineer",
            "company": "Axine Labs",
            "location": "Remote",
            "url": "https://wellfound.com/jobs/4461811",
            "description": "Build digital workforce solutions",
            "compensation": "$40k – $70k",
            "equity": "0.25% – 1.0%",
            "remote": True,
            "posted": "2026-07-13",
        },
        {
            "id": "wf-1002",
            "title": "Business Growth Lead - EdTech",
            "company": "Friss India",
            "location": "Pune + remote",
            "url": "https://wellfound.com/jobs/4458062",
            "compensation": "$30k – $60k",
            "remote": True,
            "posted": "2026-07-12",
        },
    ]
