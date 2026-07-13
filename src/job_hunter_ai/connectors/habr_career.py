"""Habr Career connector (Phase 8 stub).

Russian tech board. For MVP stub + fixture.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.connectors.base import (
    Connector,
    FetchResult,
    make_content_hash,
    utcnow,
)


class HabrCareerConnector(Connector):
    def __init__(self, source_name: str = "habr_career", jobs: list[dict] | None = None) -> None:
        super().__init__(source_name, "job_board")
        self.jobs = jobs or []

    def fetch(self, *, cursor_value: str | None = None, limit: int | None = None) -> FetchResult:
        now = utcnow()
        records = []
        for idx, job in enumerate(self.jobs):
            if not isinstance(job, dict):
                continue
            title = job.get("title")
            if not title:
                continue
            external_id = str(job.get("id", idx))
            url = job.get("url", f"https://career.habr.com/vacancies/{external_id}")
            payload = {"id": external_id, "title": title, "company": job.get("company"), "location": job.get("location")}
            record = RawSourceRecord(
                source_name=self.source_name,
                source_type=self.source_type,
                record_type="job_posting",
                external_id=external_id,
                source_url=url,
                fetched_at=now,
                discovered_at=None,
                payload=payload,
                content_hash=make_content_hash(str(payload)),
                cursor_value=cursor_value,
                metadata={"provider": "habr_career"},
            )
            records.append(record)
            if limit and len(records) >= limit:
                break
        return FetchResult(records=records, cursor_after=str(now))


def load_sample_habr_jobs() -> list[dict]:
    return [
        {"id": "habr-1", "title": "Senior Python Developer", "company": "Some RU Tech", "location": "Remote / Moscow"},
    ]
