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
        except httpx.HTTPError as exc:
            raise ConnectorNetworkError(f"WeWorkRemotely network error: {exc}") from exc
        except Exception as exc:
            raise ConnectorSchemaError(f"WeWorkRemotely fetch failed: {exc}") from exc

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


def load_sample_weworkremotely_jobs() -> list[dict]:
    return [
        {
            "title": "Head of Operations - Remote",
            "company": "Web3 Startup",
            "url": "https://weworkremotely.com/remote-jobs/12345",
        },
        {
            "title": "Program Manager, DAO Operations",
            "company": "Example DAO",
            "url": "https://weworkremotely.com/remote-jobs/67890",
        },
    ]