"""Cryptojobslist connector (Wave 1 minimal).

Priority: RSS first (https://api.cryptojobslist.com/rss.xml or /rss).

Parses title, link, description, pubDate, categories.
Maps to hard requirements / segment (ops, dao, governance, treasury).

Fallback to HTML planned for later if RSS volume is low.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.connectors.base import (
    Connector,
    ConnectorSchemaError,
    FetchResult,
    make_content_hash,
    utcnow,
)
from job_hunter_ai.connectors.http_client import HttpxDirectClient

_RSS_URL = "https://api.cryptojobslist.com/rss.xml"
_SOURCE_TYPE = "job_board"
_RECORD_TYPE = "job_posting"
_PROVIDER = "cryptojobslist"


def _parse_rss(xml_text: str) -> list[dict]:
    """Simple RSS parser for item elements."""
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ConnectorSchemaError(f"Invalid RSS XML: {e}") from e

    for item in root.findall(".//item"):
        def get(tag):
            el = item.find(tag)
            return el.text.strip() if el is not None and el.text else ""

        title = get("title")
        link = get("link")
        description = get("description")
        pub_date = get("pubDate")
        # categories often appear as multiple <category>
        categories = [c.text.strip() for c in item.findall("category") if c.text]

        if title and link:
            items.append({
                "title": title,
                "link": link,
                "description": description,
                "pubDate": pub_date,
                "categories": categories,
            })
    return items


class CryptoJobsListConnector(Connector):
    """Minimal RSS-first connector for cryptojobslist."""

    def __init__(self, source_name: str = "cryptojobslist", client: Any | None = None) -> None:
        super().__init__(source_name, _SOURCE_TYPE)
        self.client = client or HttpxDirectClient()

    def fetch(self, *, cursor_value: str | None = None, limit: int | None = None) -> FetchResult:
        try:
            # Use raw httpx for RSS (XML, not JSON)
            import httpx
            resp = httpx.get(_RSS_URL, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            xml_text = resp.text
        except Exception as exc:
            raise ConnectorSchemaError(f"Cryptojobslist RSS fetch failed: {exc}") from exc

        try:
            raw_items = _parse_rss(xml_text)
        except Exception as exc:
            raise ConnectorSchemaError(f"Cryptojobslist parse failed: {exc}") from exc

        records: list[RawSourceRecord] = []
        now = utcnow()

        for item in raw_items:
            title = item.get("title", "")
            link = item.get("link", "")
            desc = item.get("description", "")
            pub = item.get("pubDate")
            cats = item.get("categories", [])

            # Basic mapping to segment
            text_for_match = f"{title} {desc} {' '.join(cats)}".lower()
            segment_match = any(k in text_for_match for k in [
                "ops", "operations", "dao", "governance", "treasury", "contributor", "program"
            ])

            payload = {
                "title": title,
                "link": link,
                "description": desc,
                "pubDate": pub,
                "categories": cats,
                "segment_match": segment_match,
            }

            record = RawSourceRecord(
                source_name=self.source_name,
                source_type=self.source_type,
                record_type=_RECORD_TYPE,
                external_id=link or title[:50],
                source_url=link,
                fetched_at=now,
                discovered_at=self._parse_pubdate(pub),
                payload=payload,
                content_hash=make_content_hash(f"{title}|{link}"),
                cursor_value=cursor_value,
                metadata={
                    "provider": _PROVIDER,
                    "categories": cats,
                    "segment_match": segment_match,
                },
            )
            records.append(record)

            if limit and len(records) >= limit:
                break

        if not records:
            # Allow empty for now (RSS can be sparse)
            pass

        return FetchResult(records=records, cursor_after=str(now))

    def _parse_pubdate(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            # RSS dates are often like "Wed, 15 Jul 2026 10:00:00 +0000"
            return datetime.strptime(value[:25], "%a, %d %b %Y %H:%M:%S")
        except Exception:
            return None


# Convenience
def fetch_cryptojobslist_rss(limit: int | None = 20) -> list[dict]:
    conn = CryptoJobsListConnector()
    res = conn.fetch(limit=limit)
    return [r.payload for r in res.records]
