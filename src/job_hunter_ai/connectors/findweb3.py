"""findweb3.com connector - focused on /jobs/dao and similar high-relevance DAO pages.

Very high relevance for our segment (DAO Ops, Governance, Contributor roles).
"""

from __future__ import annotations

import re
from typing import Any, List

import httpx

from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.connectors.base import (
    Connector,
    ConnectorSchemaError,
    FetchResult,
    make_content_hash,
    utcnow,
)

_BASE = "https://findweb3.com"
_SOURCE_TYPE = "job_board"
_PROVIDER = "findweb3"


class FindWeb3Connector(Connector):
    """Scraper for findweb3.com DAO-focused listings."""

    def __init__(
        self,
        source_name: str = "findweb3",
        paths: List[str] | None = None,
        client: Any | None = None,
    ) -> None:
        super().__init__(source_name, _SOURCE_TYPE)
        self.paths = paths or ["/jobs/dao"]
        self._client = client or httpx.Client(timeout=20, follow_redirects=True)

    def _fetch(self, path: str) -> str:
        url = f"{_BASE}{path}"
        try:
            r = self._client.get(url)
            r.raise_for_status()
            return r.text
        except Exception as e:
            raise ConnectorSchemaError(f"findweb3 fetch failed {url}: {e}") from e

    def _parse(self, html: str, page_url: str) -> list[dict]:
        jobs = []
        # Extract headings as job titles (common pattern)
        for h in re.findall(r"<h[2-4][^>]*>(.*?)</h[2-4]>", html, re.DOTALL):
            title = re.sub(r"<[^>]+>", " ", h).strip()
            title = re.sub(r"\s+", " ", title).strip()
            if len(title) < 6:
                continue

            # Try to build link
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower())[:50]
            url = f"{page_url}#{slug}"

            relevant = any(k in title.lower() for k in ["ops", "dao", "governance", "treasury", "contributor", "program"])

            jobs.append({
                "title": title,
                "url": url,
                "source_page": page_url,
                "segment_relevant": relevant,
            })

        # dedup
        seen = set()
        out = []
        for j in jobs:
            if j["title"] not in seen:
                seen.add(j["title"])
                out.append(j)
        return out

    def fetch(self, *, cursor_value: str | None = None, limit: int | None = None) -> FetchResult:
        records = []
        now = utcnow()

        for path in self.paths:
            page_url = f"{_BASE}{path}"
            try:
                html = self._fetch(path)
            except Exception:
                continue

            raw = self._parse(html, page_url)
            for item in raw:
                payload = {
                    "title": item["title"],
                    "url": item["url"],
                    "source_page": item["source_page"],
                    "segment_relevant": item.get("segment_relevant"),
                }
                rec = RawSourceRecord(
                    source_name=self.source_name,
                    source_type=self.source_type,
                    record_type="job_posting",
                    external_id=item["url"],
                    source_url=item["url"],
                    fetched_at=now,
                    discovered_at=None,
                    payload=payload,
                    content_hash=make_content_hash(item["title"]),
                    cursor_value=cursor_value,
                    metadata={
                        "provider": _PROVIDER,
                        "path": path,
                        "segment_relevant": item.get("segment_relevant"),
                    },
                )
                records.append(rec)
                if limit and len(records) >= limit:
                    break
            if limit and len(records) >= limit:
                break

        return FetchResult(records=records, cursor_after=str(now))
