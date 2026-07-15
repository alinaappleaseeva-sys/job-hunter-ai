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
        """Extract job titles + real job detail links.

        web3.career uses real links in the form:
            /some-long-slug-with-company/151374

        The h2/h3 titles sit inside or next to <a href=".../ID">.
        We prioritize capturing the actual href.
        """
        jobs = []

        # Best: capture <a href=".../NUMBER"> containing an h2/h3
        link_title_pairs = re.findall(
            r'<a[^>]+href="(/[^"]+/\d+)"[^>]*>.*?<h[23][^>]*>(.*?)</h[23]>',
            html,
            re.DOTALL | re.I
        )

        for href, raw_title in link_title_pairs:
            title = re.sub(r"<[^>]+>", " ", raw_title).strip()
            title = re.sub(r"\s+", " ", title).strip()

            if len(title) < 8:
                continue

            # Light cleanup of polluted titles
            clean_title = title
            m = re.search(r"^(.*? (?:Manager|Lead|Head|Director|Officer|Coordinator))", title, re.I)
            if m and len(m.group(1)) > 8:
                clean_title = m.group(1).strip()

            full_url = f"https://web3.career{href}"

            # Try to pull company from the slug (part before the final /ID)
            company = None
            parts = href.strip("/").split("/")
            if len(parts) >= 2:
                company_part = parts[-2]
                cm = re.search(r"([A-Za-z0-9]+)$", company_part)
                if cm:
                    company = cm.group(1).title()

            jobs.append({
                "title": clean_title,
                "raw_title": title,
                "company": company or "Unknown",
                "url": full_url,
                "source_page": page_url,
                "real_href": href,
            })

        # Dedup by real URL
        seen = set()
        unique = []
        for j in jobs:
            if j["url"] not in seen:
                seen.add(j["url"])
                unique.append(j)

        # Fallback (should rarely trigger)
        if not unique:
            for raw_title in re.findall(r"<h[2-3][^>]*>(.*?)</h[2-3]>", html, re.DOTALL | re.I):
                title = re.sub(r"<[^>]+>", " ", raw_title).strip()
                if len(title) < 8: continue
                slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:70]
                jobs.append({
                    "title": title,
                    "company": "Unknown",
                    "url": f"https://web3.career/jobs/{slug}",
                    "source_page": page_url,
                })
            for j in jobs:
                if j["url"] not in seen:
                    seen.add(j["url"])
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
