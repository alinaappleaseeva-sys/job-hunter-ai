"""Solana Jobs connector (Phase 8 stub).

Powered by Getro. For MVP we use sample data.
Real implementation would parse the Getro-powered board.
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


class SolanaJobsConnector(Connector):
    """Solana ecosystem jobs connector (MVP stub)."""

    def __init__(self, source_name: str = "solana", jobs: list[dict] | None = None) -> None:
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
            url = job.get("url") or f"https://jobs.solana.com/jobs/{external_id}"

            payload = {
                "id": external_id,
                "title": title,
                "company": company,
                "location": job.get("location"),
                "url": url,
                "description": job.get("description"),
                "compensation": job.get("compensation"),
                "level": job.get("level"),
                "posted": job.get("posted"),
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
                metadata={"provider": "solana", "ecosystem": "solana"},
            )
            records.append(record)

            if limit and len(records) >= limit:
                break

        if not records and self.jobs:
            raise ConnectorEmptyResponseError("No usable Solana jobs in sample")

        return FetchResult(records=records, cursor_after=str(now))

    def _parse_date(self, value: Any) -> datetime | None:
        if not value:
            return None
        try:
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(value)
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None


def load_sample_solana_jobs() -> list[dict]:
    """Sample Solana ecosystem jobs (Phase 8)."""
    return [
        {
            "id": "sol-2001",
            "title": "Trading Growth Lead, Americas",
            "company": "Solana Foundation",
            "location": "United States ; Remote",
            "url": "https://jobs.solana.com/jobs/2001",
            "description": "Lead trading growth for Solana ecosystem",
            "level": "Mid-Senior",
            "posted": "2026-07-13",
        },
        {
            "id": "sol-2002",
            "title": "Quality Assurance Automation Engineer",
            "company": "Ergonia",
            "location": "United States",
            "compensation": "USD 70k-100k / year + Equity",
            "level": "Mid-Senior",
            "posted": "2026-07-10",
        },
    ]
