"""web3.career connector - HTML polling for key filtered pages.

Priority pages:
- /operations-jobs
- /dao-jobs
- /treasury-jobs (if present)

Realistic HTML scraping for Web3 Ops / DAO / Governance / Treasury roles.

Current implementation uses httpx + regex (robust against heavy JS pages by extracting visible titles).
Future: can switch to API if discovered or use Playwright for full render.
"""

from __future__ import annotations

import re
from datetime import datetime
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

_BASE = "https://web3.career"
_SOURCE_TYPE = "job_board"
_RECORD_TYPE = "job_posting"
_PROVIDER = "web3career"


class Web3CareerConnector(Connector):
    """Polls web3.career filtered listing pages and extracts jobs."""

    DEFAULT_PATHS = [
        "operations-jobs",
        "dao-jobs",
        # "treasury-jobs",  # add when confirmed
    ]

    def __init__(
        self,
        source_name: str = "web3career",
        paths: List[str] | None = None,
        client: Any | None = None,
    ) -> None:
        super().__init__(source_name, _SOURCE_TYPE)
        self.paths = paths or self.DEFAULT_PATHS
        self._client = client or httpx.Client(timeout=25, follow_redirects=True)

    def _fetch_page(self, path: str) -> str:
        url = f"{_BASE}/{path.lstrip('/')}"
        try:
            resp = self._client.get(url)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            raise ConnectorSchemaError(f"Failed to fetch {url}: {exc}") from exc

    def _extract_jobs_from_html(self, html: str, page_url: str) -> List[dict]:
        """Extract job titles from the page.

        web3.career pages surface job titles in h2/h3 elements.
        We also capture any nearby company-like text.
        """
        jobs = []

        # Primary: h2 and h3 as titles (these are the visible job headings)
        headings = re.findall(r"<h[2-3][^>]*>(.*?)</h[2-3]>", html, re.DOTALL | re.I)

        for raw_title in headings:
            title = re.sub(r"<[^>]+>", " ", raw_title).strip()
            title = re.sub(r"\s+", " ", title).strip()

            if len(title) < 8:
                continue

            # Heuristic company extraction (often appears near title or in meta)
            company = None
            company_match = re.search(r"at ([A-Z][A-Za-z0-9\s&\.]+)", title)
            if company_match:
                company = company_match.group(1).strip()

            # Construct a usable link (web3.career often uses /jobs/<slug> or the page itself)
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
            link = f"{page_url}#{slug}"   # best-effort deep link; real links may be JS-driven

            jobs.append({
                "title": title,
                "company": company or "Unknown",
                "url": link,
                "source_page": page_url,
            })

        # Deduplicate
        seen = set()
        unique = []
        for j in jobs:
            key = j["title"][:50]
            if key not in seen:
                seen.add(key)
                unique.append(j)

        return unique

    def fetch(self, *, cursor_value: str | None = None, limit: int | None = None) -> FetchResult:
        records: list[RawSourceRecord] = []
        now = utcnow()

        for path in self.paths:
            page_url = f"{_BASE}/{path.lstrip('/')}"
            try:
                html = self._fetch_page(path)
            except Exception:
                continue

            raw_jobs = self._extract_jobs_from_html(html, page_url)

            for item in raw_jobs:
                title = item["title"]
                url = item["url"]

                # Segment relevance
                text_blob = f"{title} {item.get('company', '')}".lower()
                relevant = any(k in text_blob for k in [
                    "ops", "operation", "dao", "governance", "treasury",
                    "contributor", "program manager", "head of ops", "senior ops"
                ])

                payload = {
                    "title": title,
                    "company": item.get("company"),
                    "url": url,
                    "source_page": item.get("source_page"),
                    "segment_relevant": relevant,
                }

                rec = RawSourceRecord(
                    source_name=self.source_name,
                    source_type=self.source_type,
                    record_type=_RECORD_TYPE,
                    external_id=url or title,
                    source_url=url,
                    fetched_at=now,
                    discovered_at=None,
                    payload=payload,
                    content_hash=make_content_hash(title + url),
                    cursor_value=cursor_value,
                    metadata={
                        "provider": _PROVIDER,
                        "path": path,
                        "segment_relevant": relevant,
                    },
                )
                records.append(rec)

                if limit and len(records) >= limit:
                    break

            if limit and len(records) >= limit:
                break

        return FetchResult(records=records, cursor_after=str(now))


# Quick helpers for common pages
def fetch_web3career_operations(limit: int = 20):
    c = Web3CareerConnector(paths=["operations-jobs"])
    return c.fetch(limit=limit).records


def fetch_web3career_dao(limit: int = 20):
    c = Web3CareerConnector(paths=["dao-jobs"])
    return c.fetch(limit=limit).records
