"""Minimal fetch stubs for protocol career/governance pages (Wave 1).

Uses httpx + regex (no bs4 dependency for now).
Focus: Lido, Optimism, Arbitrum, karpatkey.

Run:
    PYTHONPATH=src python sources/fetch_protocol_stubs.py
"""

import json
import re
from datetime import datetime
from pathlib import Path

import httpx

PROTOCOLS = [
    {
        "name": "Lido",
        "slug": "lido",
        "careers": "https://lido.fi/careers",
        "governance": "https://research.lido.fi/",
    },
    {
        "name": "Optimism",
        "slug": "optimism",
        "careers": "https://jobs.theblockchainassociation.org/companies/optimism-foundation-2",
        "governance": "https://gov.optimism.io/",
    },
    {
        "name": "Arbitrum",
        "slug": "arbitrum",
        "careers": "https://jobs.arbitrum.io/",
        "governance": "https://forum.arbitrum.foundation/",
    },
    {
        "name": "karpatkey",
        "slug": "karpatkey",
        "careers": "https://www.karpatkey.com/careers",
        "governance": "https://snapshot.box/#/s:karpatkey.eth",
    },
]

JOB_KEYWORDS = [
    "ops", "operations", "dao", "governance", "treasury", "contributor",
    "program", "head of", "senior", "lead", "manager", "role", "position", "hiring"
]


def extract_job_links(html: str, base_url: str) -> list[dict]:
    """Very lightweight extraction of job-like links."""
    results = []
    # Find <a> tags
    links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S)
    for href, text in links:
        text_clean = re.sub(r'<[^>]+>', '', text).strip()
        combined = (text_clean + " " + href).lower()
        if any(kw in combined for kw in JOB_KEYWORDS):
            full_url = href if href.startswith("http") else base_url.rstrip("/") + "/" + href.lstrip("/")
            results.append({
                "title": text_clean[:120],
                "url": full_url,
                "source": base_url,
            })
    # Dedup
    seen = set()
    deduped = []
    for r in results:
        key = r["url"]
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    return deduped[:10]


def fetch_page(url: str) -> str:
    try:
        r = httpx.get(url, timeout=20, follow_redirects=True)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return ""


def main():
    out = {
        "timestamp": datetime.utcnow().isoformat(),
        "protocols": []
    }

    for proto in PROTOCOLS:
        print(f"Fetching {proto['name']}...")
        careers_html = fetch_page(proto["careers"])
        gov_html = fetch_page(proto["governance"])

        careers_jobs = extract_job_links(careers_html, proto["careers"]) if careers_html else []
        gov_jobs = extract_job_links(gov_html, proto["governance"]) if gov_html else []

        entry = {
            "name": proto["name"],
            "slug": proto["slug"],
            "careers_url": proto["careers"],
            "governance_url": proto["governance"],
            "careers_hits": len(careers_jobs),
            "governance_hits": len(gov_jobs),
            "jobs": careers_jobs + gov_jobs,
        }
        out["protocols"].append(entry)

        print(f"  Careers hits: {len(careers_jobs)}, Governance hits: {len(gov_jobs)}")

    # Save
    out_path = Path("evals/runs/protocol_stubs_latest.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\nSaved to {out_path}")

    # Print summary
    print("\n=== Summary ===")
    for p in out["protocols"]:
        print(f"{p['name']}: {p['careers_hits'] + p['governance_hits']} job-like items")


if __name__ == "__main__":
    main()
