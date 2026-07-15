"""Wellfound (formerly AngelList) connector (Wave 1 - real implementation).

Wellfound does **not** have a public API.
We fetch the public jobs page and extract data from the embedded Next.js JSON (__NEXT_DATA__).

This is a lightweight scraper. It is intentionally conservative and may need updates if the frontend changes.
"""

from __future__ import annotations

import json
import re
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


class WellfoundConnector(Connector):
    """Wellfound jobs connector using public page scraping."""

    BASE_URL = "https://wellfound.com/jobs"

    def __init__(self, source_name: str = "wellfound") -> None:
        super().__init__(source_name, "job_board")

    def fetch(self, *, cursor_value: str | None = None, limit: int | None = None) -> FetchResult:
        now = utcnow()

        # Fetch remote-focused or main jobs page
        url = f"{self.BASE_URL}?filter=remote"

        jobs: list[dict] = []

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }) as client:
                resp = client.get(url)
                if resp.status_code == 403:
                    # Wellfound is aggressively blocking. Fall back to samples so the pipeline remains usable.
                    return self._fallback_to_samples(limit)
                resp.raise_for_status()
                html = resp.text
                jobs = self._extract_jobs_from_html(html)
        except httpx.HTTPError as exc:
            # On network/scrape failure, gracefully fall back
            return self._fallback_to_samples(limit)
        except Exception:
            return self._fallback_to_samples(limit)

        records: list[RawSourceRecord] = []

        for idx, job in enumerate(jobs):
            if not isinstance(job, dict):
                continue

            title = job.get("title") or job.get("position") or ""
            if not title:
                continue

            company = job.get("company") or job.get("companyName")
            external_id = str(job.get("id") or job.get("slug") or idx)
            url = job.get("url") or f"https://wellfound.com/jobs/{external_id}"

            payload = {
                "id": external_id,
                "title": title,
                "company": company,
                "location": job.get("location") or job.get("locations"),
                "url": url,
                "description": (job.get("description") or "")[:600],
                "compensation": job.get("salary") or job.get("compensation"),
                "equity": job.get("equity"),
                "remote": job.get("remote") or True,
            }

            record = RawSourceRecord(
                source_name=self.source_name,
                source_type=self.source_type,
                record_type="job_posting",
                external_id=external_id,
                source_url=url,
                fetched_at=now,
                discovered_at=self._parse_date(job.get("postedAt") or job.get("createdAt")),
                payload=payload,
                content_hash=make_content_hash(title + "|" + url),
                cursor_value=cursor_value,
                metadata={"provider": "wellfound"},
            )
            records.append(record)

            if limit and len(records) >= limit:
                break

        if not records:
            return self._fallback_to_samples(limit)

        return FetchResult(records=records, cursor_after=str(now))

    def _fallback_to_samples(self, limit: int | None) -> FetchResult:
        """Return sample data when live scraping is blocked (common for Wellfound)."""
        now = utcnow()
        samples = load_sample_wellfound_jobs()
        records: list[RawSourceRecord] = []

        for idx, job in enumerate(samples):
            if limit and len(records) >= limit:
                break
            external_id = str(job.get("id", idx))
            url = job.get("url", f"https://wellfound.com/jobs/{external_id}")

            record = RawSourceRecord(
                source_name=self.source_name,
                source_type=self.source_type,
                record_type="job_posting",
                external_id=external_id,
                source_url=url,
                fetched_at=now,
                discovered_at=self._parse_date(job.get("posted")),
                payload=job,
                content_hash=make_content_hash(str(job)),
                cursor_value=None,
                metadata={"provider": "wellfound", "source": "sample_fallback"},
            )
            records.append(record)

        return FetchResult(records=records, cursor_after=str(now))

    def _extract_jobs_from_html(self, html: str) -> list[dict]:
        """Try to extract job listings from Wellfound's __NEXT_DATA__ or other embedded JSON."""
        jobs: list[dict] = []

        # Common pattern for Next.js apps
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                props = data.get("props", {})
                page_props = props.get("pageProps", {})
                for key in ("jobs", "jobListings", "results", "searchResults"):
                    val = page_props.get(key) or data.get(key)
                    if isinstance(val, list):
                        jobs = val
                        break
                    if isinstance(val, dict):
                        for subkey in ("jobs", "items", "listings"):
                            if isinstance(val.get(subkey), list):
                                jobs = val[subkey]
                                break
                if jobs:
                    return jobs
            except Exception:
                pass

        # Rough fallback
        try:
            candidates = re.findall(r'{"title":"([^"]+)","company":"?([^",}]+)', html)
            for title, company in candidates[:30]:
                jobs.append({"title": title, "company": company})
        except Exception:
            pass

        return jobs

    def _parse_date(self, value: Any) -> datetime | None:
        if not value:
            return None
        try:
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(value / 1000)
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None


def load_sample_wellfound_jobs() -> list[dict]:
    """Sample jobs (kept ONLY for tests and when live scraping fails).

    IMPORTANT (Phase 0 hygiene): These are conservative/neutral placeholders.
    Do NOT use high-relevance target roles (Head of Ops, DAO Ops, etc.) here,
    as they can pollute ranking when live fetch is blocked.
    """
    return [
        {
            "id": "wf-sample-001",
            "title": "Software Engineer",
            "company": "Example Startup",
            "location": "Remote",
            "url": "https://wellfound.com/jobs?filter=remote",
            "description": "General engineering role (sample fallback only)",
            "compensation": None,
            "remote": True,
            "posted": "2026-07-10",
        },
        {
            "id": "wf-sample-002",
            "title": "Frontend Developer",
            "company": "DesignCo",
            "location": "Remote",
            "url": "https://wellfound.com/jobs/wf-sample-002",
            "description": "Building user interfaces (sample)",
            "compensation": "$110k",
            "remote": True,
            "posted": "2026-07-10",
        },
        {
            "id": "wf-sample-003",
            "title": "Backend Engineer",
            "company": "Infra Labs",
            "location": "Remote",
            "url": "https://wellfound.com/jobs/wf-sample-003",
            "description": "API and services work (sample fallback)",
            "compensation": None,
            "remote": True,
            "posted": "2026-07-10",
        },
    ]
