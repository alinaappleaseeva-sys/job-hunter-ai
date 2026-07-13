"""Arc.dev connector (Wave 1).

Remote tech roles, strong for international remote work.
For MVP we provide structure ready for their public listings.
"""

from __future__ import annotations

from typing import Any

from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.connectors.base import Connector, FetchResult, make_content_hash, utcnow


class ArcDevConnector(Connector):
    """Arc.dev remote jobs connector (Wave 1 skeleton + samples)."""

    def __init__(self, source_name: str = "arcdev") -> None:
        super().__init__(source_name, "job_board")

    def fetch(self, *, cursor_value: str | None = None, limit: int | None = None) -> FetchResult:
        now = utcnow()
        # Placeholder: in real impl fetch from arc.dev public data
        # For now return samples (easy to replace with real fetch)
        samples = load_sample_arcdev_jobs()
        records = []
        for idx, job in enumerate(samples):
            title = job.get("title", "")
            url = job.get("url", "")
            record = RawSourceRecord(
                source_name=self.source_name,
                source_type=self.source_type,
                record_type="job_posting",
                external_id=str(job.get("id", idx)),
                source_url=url,
                fetched_at=now,
                discovered_at=None,
                payload={"title": title, "company": job.get("company"), "url": url},
                content_hash=make_content_hash(title + url),
                cursor_value=cursor_value,
                metadata={"provider": "arcdev"},
            )
            records.append(record)
            if limit and len(records) >= limit:
                break
        return FetchResult(records=records, cursor_after=str(now))


def load_sample_arcdev_jobs() -> list[dict]:
    return [
        {"id": "arc-1", "title": "Head of Operations", "company": "Remote Startup", "url": "https://arc.dev/remote"},
        {"id": "arc-2", "title": "Program Manager - Crypto", "company": "Web3 Co", "url": "https://arc.dev/remote"},
        {"id": "arc-3", "title": "Senior Project Manager (Remote)", "company": "Tech DAO", "url": "https://arc.dev/remote"},
    ]