"""Improved fetch stubs for protocol career / opportunities / governance pages.

Key improvements:
- Supports 'careers' + 'opportunities' sections in seeds.
- Automatic discovery of common job paths (/opportunities, /jobs, /careers, /hiring, etc.).
- Proper relative URL resolution (urljoin).
- Better extraction for Lido-style and Ashby-style pages.
- Focus on Ops/Governance/Treasury/Contributor roles.

Run:
    PYTHONPATH=src python sources/fetch_protocol_stubs.py
"""

import json
import re
from datetime import datetime, date
from pathlib import Path
from typing import Any, List, Dict
from urllib.parse import urljoin, urlparse

import httpx
import yaml

SEEDS_PATH = Path(__file__).parent / "protocol_seeds.yaml"
OUTPUT_PATH = Path("evals/runs/protocol_stubs_latest.json")

JOB_KEYWORDS = [
    "ops", "operations", "dao", "governance", "treasury", "contributor",
    "program", "head of", "senior", "lead", "manager", "role", "position",
    "hiring", "coordinator", "chief of staff", "strategic", "project"
]

COMMON_JOB_PATHS = [
    "/opportunities",
    "/jobs",
    "/careers",
    "/hiring",
    "/open-roles",
    "/about/careers",
    "/company/careers",
]

ASHBY_DOMAINS = ["jobs.ashbyhq.com", "ashbyhq.com"]


def load_high_priority_job_sources(limit: int = 15) -> List[Dict]:
    """Load protocols and collect all relevant job/opportunity URLs from seeds."""
    with open(SEEDS_PATH) as f:
        data = yaml.safe_load(f) or {}

    protos = []
    for p in data.get("protocols", []):
        if p.get("priority") != "high":
            continue

        name = p["name"]
        website = p.get("website", "")
        slug = p.get("slug", name.lower().replace(" ", "-"))

        # Collect all candidate career/opportunity URLs
        candidates = []

        # From careers
        for c in p.get("careers", []) or []:
            if isinstance(c, dict) and c.get("url"):
                candidates.append(c["url"])
            elif isinstance(c, str):
                candidates.append(c)

        # From dedicated opportunities section (new)
        for o in p.get("opportunities", []) or []:
            if isinstance(o, dict) and o.get("url"):
                candidates.append(o["url"])
            elif isinstance(o, str):
                candidates.append(o)

        # From governance we still fetch separately
        gov_urls = []
        for g in p.get("governance", []) or []:
            if isinstance(g, dict) and g.get("url"):
                gov_urls.append(g["url"])
            elif isinstance(g, str):
                gov_urls.append(g)

        if candidates or gov_urls:
            protos.append({
                "name": name,
                "slug": slug,
                "website": website,
                "candidates": list(dict.fromkeys(candidates)),  # dedup preserve order
                "governance": gov_urls[:2],  # limit
            })

        if len(protos) >= limit:
            break

    return protos


def discover_alternative_job_pages(website: str, known_urls: List[str]) -> List[str]:
    """
    Try common alternative paths for job pages if the primary ones gave poor results.
    """
    if not website:
        return []

    discovered = []
    parsed = urlparse(website)
    base = f"{parsed.scheme}://{parsed.netloc}"

    for path in COMMON_JOB_PATHS:
        candidate = urljoin(base + "/", path.lstrip("/"))
        # Avoid adding exact duplicates of what we already have
        if not any(candidate.rstrip("/") == k.rstrip("/") for k in known_urls):
            discovered.append(candidate)

    return discovered[:5]  # limit noise


def fetch(url: str) -> str:
    try:
        r = httpx.get(url, timeout=20, follow_redirects=True)
        return r.text if r.status_code == 200 else ""
    except Exception:
        return ""


def resolve_url(href: str, base_url: str) -> str:
    """Properly resolve relative URLs."""
    if not href:
        return ""
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        return "https:" + href
    return urljoin(base_url, href)


def extract_job_like_items(html: str, base_url: str) -> List[Dict]:
    """
    Improved extraction:
    - Better relative link handling with urljoin
    - Strongly prioritizes real /opportunities/ and /jobs/ slugs
    - Catches Ashby application links
    - Good for Lido-style dedicated opportunities pages
    """
    results = []

    links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S)

    for href, text in links:
        text_clean = re.sub(r'<[^>]+>', '', text).strip()
        full_url = resolve_url(href, base_url)
        combined = (text_clean + " " + full_url).lower()

        is_real_opportunity = bool(re.search(r'/opportunities/[^/]+', full_url)) or \
                              bool(re.search(r'/jobs/[^/]+', full_url))
        is_job_path = any(p in full_url.lower() for p in ["/opportunities", "/jobs", "/careers", "/hiring"])
        has_keyword = any(kw in combined for kw in JOB_KEYWORDS)

        if is_real_opportunity or is_job_path or has_keyword:
            is_ashby = any(domain in full_url for domain in ASHBY_DOMAINS)

            results.append({
                "title": text_clean[:160] or "(no title text)",
                "url": full_url,
                "source": base_url,
                "is_ashby": is_ashby,
                "is_real_opportunity": is_real_opportunity,
            })

    # Dedup
    seen = set()
    deduped = []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            deduped.append(r)

    # Strong priority: real opportunity slugs first, then Ashby, then others
    def priority(item):
        if item.get("is_real_opportunity"):
            return 0
        if item.get("is_ashby"):
            return 1
        u = item["url"].lower()
        if "/opportunities" in u or "/jobs" in u:
            return 2
        return 3

    deduped.sort(key=priority)
    return deduped[:10]
    return deduped[:10]


def run_stubs() -> Dict:
    protocols = load_high_priority_job_sources()
    print(f"Loaded {len(protocols)} high-priority protocols from seeds")

    results = {}

    for p in protocols:
        name = p["name"]
        website = p.get("website", "")
        candidates = p.get("candidates", [])

        # Auto-discover more paths if we have few candidates
        if len(candidates) < 2 and website:
            extra = discover_alternative_job_pages(website, candidates)
            candidates.extend(extra)

        res = {
            "careers_hits": 0,
            "governance_hits": 0,
            "discovered_paths": 0,
            "items": [],
            "ashby_links_found": 0,
        }

        all_items = []

        # Fetch candidate job/opportunity pages
        for url in candidates:
            html = fetch(url)
            if not html:
                continue
            items = extract_job_like_items(html, url)
            for it in items:
                if it.get("is_ashby"):
                    res["ashby_links_found"] += 1
            all_items.extend(items)

        # Also fetch governance
        for gov_url in p.get("governance", []):
            html = fetch(gov_url)
            if html:
                items = extract_job_like_items(html, gov_url)
                all_items.extend(items)
                res["governance_hits"] += len(items)

        # Dedup everything
        seen = set()
        final_items = []
        for it in all_items:
            if it["url"] not in seen:
                seen.add(it["url"])
                final_items.append(it)

        res["items"] = final_items[:12]
        res["careers_hits"] = len([i for i in final_items if not any(g in i["source"] for g in ["gov", "forum", "snapshot", "research"])])
        # Rough split (governance hits already counted separately above in some cases)

        # Count discovered
        res["discovered_paths"] = len([c for c in candidates if c not in (p.get("candidates") or [])])

        results[name] = res

        ashby_note = f", ashby={res['ashby_links_found']}" if res["ashby_links_found"] else ""
        disc_note = f", discovered={res['discovered_paths']}" if res["discovered_paths"] else ""
        print(f"  {name}: careers/opp_hits={res['careers_hits']}, governance={res['governance_hits']}{ashby_note}{disc_note}")

    output = {
        "timestamp": datetime.now().isoformat(),
        "date": str(date.today()),
        "protocols_checked": len(protocols),
        "improvements": [
            "automatic path discovery (/opportunities, /jobs, /careers)",
            "dedicated opportunities section support",
            "proper urljoin for relative links",
            "Ashby link detection"
        ],
        "results": results,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to {OUTPUT_PATH}")
    return output


if __name__ == "__main__":
    run_stubs()
