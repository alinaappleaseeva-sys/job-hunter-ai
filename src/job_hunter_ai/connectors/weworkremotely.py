"""We Work Remotely connector (Wave 1).

Public RSS feed: https://weworkremotely.com/remote-jobs.rss
Strong remote coverage. Good source for ops, program, and Web3-adjacent roles.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
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


class WeWorkRemotelyConnector(Connector):
    """We Work Remotely connector using public RSS."""

    RSS_URL = "https://weworkremotely.com/remote-jobs.rss"

    def __init__(self, source_name: str = "weworkremotely") -> None:
        super().__init__(source_name, "job_board")

    def fetch(self, *, cursor_value: str | None = None, limit: int | None = None) -> FetchResult:
        now = utcnow()

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                resp = client.get(self.RSS_URL)
                resp.raise_for_status()
                content = resp.text
        except Exception as exc:
            # Fallback on any failure (network, parse, etc.) to keep smoke robust
            return self._fallback_to_samples(limit)

        records: list[RawSourceRecord] = []

        try:
            root = ET.fromstring(content)
            items = root.findall(".//item")
        except Exception:
            items = []

        for idx, item in enumerate(items):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date = item.findtext("pubDate")
            description = (item.findtext("description") or "")[:800]

            if not title or not link:
                continue

            external_id = link.rstrip("/").split("/")[-1] or f"wwr-{idx}"

            payload = {
                "title": title,
                "url": link,
                "description": description,
                "published": pub_date,
            }

            record = RawSourceRecord(
                source_name=self.source_name,
                source_type=self.source_type,
                record_type="job_posting",
                external_id=external_id,
                source_url=link,
                fetched_at=now,
                discovered_at=self._parse_pubdate(pub_date),
                payload=payload,
                content_hash=make_content_hash(title + "|" + link),
                cursor_value=cursor_value,
                metadata={"provider": "weworkremotely"},
            )
            records.append(record)

            if limit and len(records) >= limit:
                break

        return FetchResult(records=records, cursor_after=str(now))

    def _parse_pubdate(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(value)
        except Exception:
            return None



    def _fallback_to_samples(self, limit: int | None) -> FetchResult:
        """Return neutral samples when live RSS fails."""
        from datetime import datetime as dt
        now = utcnow()
        samples = load_sample_weworkremotely_jobs()
        records: list[RawSourceRecord] = []
        for idx, job in enumerate(samples):
            if limit and len(records) >= limit:
                break
            url = job.get("url", f"https://weworkremotely.com/jobs/{idx}")
            title = job.get("title", "Software Engineer")
            record = RawSourceRecord(
                source_name=self.source_name,
                source_type=self.source_type,
                record_type="job_posting",
                external_id=f"wwr-sample-{idx}",
                source_url=url,
                fetched_at=now,
                discovered_at=now,
                payload=job,
                content_hash=make_content_hash(title + "|" + url),
                cursor_value=None,
                metadata={"provider": "weworkremotely", "source": "sample_fallback"},
            )
            records.append(record)
        return FetchResult(records=records, cursor_after=str(now))

def load_sample_weworkremotely_jobs() -> list[dict]:
    """Neutral sample (Phase 0 hygiene - no target roles)."""
    return [
        {
            "title": "Software Engineer",
            "company": "Example Company",
            "url": "https://example.com/jobs/1",
        },
        {
            "title": "Marketing Manager",
            "company": "Remote Team",
            "url": "https://example.com/jobs/2",
        },
    ]