"""Company field helpers."""

from __future__ import annotations

from urllib.parse import urlparse

_JOB_BOARD_HOST_ALIASES: dict[str, str] = {
    "jobs.lever.co": "lever.co",
    "jobs.ashbyhq.com": "ashbyhq.com",
}


def extract_company_domain(url: str | None) -> str | None:
    """Extract a registrable domain from a job or company URL."""
    if not url or not str(url).strip():
        return None
    parsed = urlparse(str(url).strip())
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return _JOB_BOARD_HOST_ALIASES.get(host, host) or None