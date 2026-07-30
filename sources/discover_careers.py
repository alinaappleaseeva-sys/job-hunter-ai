#!/usr/bin/env python3
"""
Phase 1: Career page / ATS discovery for Talent Titans (Top 100 Web3 Employers).

Lightweight discovery only — no full job scraping, no ranking.

Run:
    python sources/discover_careers.py
    # or with src in path if needed
    PYTHONPATH=src python sources/discover_careers.py
"""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
import yaml

TALENT_TITANS_PATH = Path(__file__).parent / "talent_titans_top100.yaml"
PROTOCOL_SEEDS_PATH = Path(__file__).parent / "protocol_seeds.yaml"
DISCOVERY_DIR = Path(__file__).parent / "discovery"
OUTPUT_YAML = DISCOVERY_DIR / "talent_titans_discovery.yaml"
OUTPUT_RAW_JSON = DISCOVERY_DIR / "talent_titans_discovery_raw.json"

# Concurrency and network settings
MAX_WORKERS = 3
TIMEOUT = 18.0
BACKOFF_BASE = 0.8
MAX_RETRIES = 2

COMMON_CAREERS_PATHS = [
    "/",
    "/careers",
    "/jobs",
    "/opportunities",
    "/hiring",
    "/open-roles",
    "/about/careers",
    "/company/careers",
    "/about/jobs",
    "/join-us",
]

# ATS URL patterns
ATS_PATTERNS = {
    "greenhouse": re.compile(r"boards\.greenhouse\.io/([^/?#]+)"),
    "ashby": re.compile(r"jobs\.ashbyhq\.com/([^/?#]+)|ashbyhq\.com/([^/?#]+)"),
    "lever": re.compile(r"jobs\.lever\.co/([^/?#]+)"),
    "workable": re.compile(r"(?:apply\.|jobs\.)workable\.com/([^/?#]+)"),
}

JOB_SIGNAL_WORDS = [
    "job", "jobs", "role", "roles", "position", "positions",
    "hiring", "apply", "careers", "opportunities", "openings",
    "join", "team", "work with us",
]


def load_talent_titans() -> List[Dict[str, Any]]:
    with open(TALENT_TITANS_PATH) as f:
        data = yaml.safe_load(f) or {}
    return data.get("employers", [])


def load_protocol_seeds_for_overlap() -> Dict[str, Dict]:
    """Lightweight overlap check (similar to improved logic in prepare)."""
    if not PROTOCOL_SEEDS_PATH.exists():
        return {}
    with open(PROTOCOL_SEEDS_PATH) as f:
        data = yaml.safe_load(f) or {}
    overlaps = {}
    for p in data.get("protocols", []):
        slug = p.get("slug")
        website = (p.get("website") or "").lower()
        name = (p.get("name") or "").lower()
        domains = set()
        if website:
            net = urlparse(website).netloc.lower().replace("www.", "")
            domains.add(net)
            parts = net.split(".")
            if len(parts) >= 2:
                domains.add(".".join(parts[-2:]))
        overlaps[slug] = {"slug": slug, "domains": domains, "name": name}
        for d in domains:
            overlaps[d] = {"slug": slug, "domains": domains, "name": name}
    return overlaps


def is_already_in_protocol_seeds(name: str, website: str, overlaps: Dict) -> bool:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if slug in overlaps:
        return True
    if not website:
        return False
    try:
        net = urlparse(website).netloc.lower().replace("www.", "")
        domain = ".".join(net.split(".")[-2:])
    except Exception:
        domain = ""
    for key, info in overlaps.items():
        if key == slug:
            return True
        if domain and any(d in domain or domain in d for d in info.get("domains", set())):
            return True
        if name.lower() in info.get("name", "") or info.get("name", "") in name.lower():
            return True
    return False


def detect_ats(url: str) -> Optional[Dict[str, str]]:
    """Detect ATS type and board_slug from final URL."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.strip("/")

    if "boards.greenhouse.io" in host:
        match = ATS_PATTERNS["greenhouse"].search(url)
        if match:
            return {"ats": "greenhouse", "board_slug": match.group(1)}

    if "ashbyhq.com" in host or "jobs.ashbyhq.com" in host:
        match = ATS_PATTERNS["ashby"].search(url)
        if match:
            slug = match.group(1) or match.group(2)
            return {"ats": "ashby", "board_slug": slug}

    if "jobs.lever.co" in host:
        match = ATS_PATTERNS["lever"].search(url)
        if match:
            return {"ats": "lever", "board_slug": match.group(1)}

    if "workable.com" in host:
        match = ATS_PATTERNS["workable"].search(url)
        if match:
            return {"ats": "workable", "board_slug": match.group(1)}

    return None


def has_job_signals(html: str, final_url: str) -> bool:
    """Light signal: 200 + enough job-related content or links."""
    if not html:
        return False

    text = (html + " " + final_url).lower()
    count = sum(1 for word in JOB_SIGNAL_WORDS if word in text)

    # Count job-like links
    links = re.findall(r'href=["\']([^"\']*(?:job|role|career|apply|hire|position|opening)[^"\']*)["\']', html, re.I)
    link_count = len(links)

    return (count + link_count) >= 2


def check_url(url: str, client: httpx.Client) -> Dict[str, Any]:
    """Perform one check with retries + backoff."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = client.get(url, timeout=TIMEOUT, follow_redirects=True)
            status = resp.status_code
            final_url = str(resp.url)

            ats_info = detect_ats(final_url)
            html = resp.text if status < 400 else ""

            signals = has_job_signals(html, final_url) or bool(ats_info)

            confidence = "low"
            if ats_info and status == 200:
                confidence = "high"
            elif status == 200 and signals:
                confidence = "medium"

            return {
                "url": final_url,
                "status": status,
                "type": "ats" if ats_info else "careers_page",
                "ats": ats_info["ats"] if ats_info else None,
                "board_slug": ats_info["board_slug"] if ats_info else None,
                "has_job_signals": signals,
                "confidence": confidence,
            }
        except Exception as e:
            if attempt == MAX_RETRIES:
                return {
                    "url": url,
                    "status": 0,
                    "type": "error",
                    "ats": None,
                    "board_slug": None,
                    "has_job_signals": False,
                    "confidence": "low",
                    "error": str(e)[:100],
                }
            time.sleep(BACKOFF_BASE * (attempt + 1))
    return {"url": url, "status": 0, "confidence": "low"}


def discover_for_employer(employer: Dict, client: httpx.Client) -> Dict[str, Any]:
    name = employer.get("name", "")
    website = employer.get("website", "") or employer.get("main", "")
    rank = employer.get("rank")

    if not website:
        return {
            "rank": rank,
            "name": name,
            "website": website,
            "already_in_protocol_seeds": False,
            "careers_candidates": [],
            "best_guess": None,
        }

    parsed = urlparse(website)
    base = f"{parsed.scheme}://{parsed.netloc}"

    candidates = []
    seen = set()

    # Root + common paths
    for path in COMMON_CAREERS_PATHS:
        full = urljoin(base + "/", path.lstrip("/"))
        if full not in seen:
            seen.add(full)
            candidates.append(full)

    # Also try the website root explicitly
    if website not in seen:
        seen.add(website)
        candidates.insert(0, website)

    results = []
    for url in candidates[:12]:  # safety cap
        res = check_url(url, client)
        if res.get("status") in (200, 301, 302) or res.get("has_job_signals"):
            results.append(res)

    # Prefer ATS, then high confidence, then medium
    def score(r):
        if r.get("ats"):
            return (0, r.get("status") == 200)
        conf = r.get("confidence", "low")
        if conf == "high":
            return (1, r.get("status") == 200)
        if conf == "medium":
            return (2, r.get("status") == 200)
        return (3, False)

    results.sort(key=score)

    careers_candidates = results[:6]  # limit noise

    # best_guess: first high or first medium with ATS preference
    best = None
    for r in results:
        if r.get("confidence") == "high":
            best = {
                "ats": r.get("ats"),
                "board_slug": r.get("board_slug"),
                "careers_url": r.get("url"),
                "confidence": "high",
            }
            break
    if not best:
        for r in results:
            if r.get("confidence") == "medium":
                best = {
                    "ats": r.get("ats"),
                    "board_slug": r.get("board_slug"),
                    "careers_url": r.get("url"),
                    "confidence": "medium",
                }
                break

    overlaps = load_protocol_seeds_for_overlap()
    already = is_already_in_protocol_seeds(name, website, overlaps)

    return {
        "rank": rank,
        "name": name,
        "website": website,
        "already_in_protocol_seeds": already,
        "careers_candidates": careers_candidates,
        "best_guess": best,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Talent Titans career/ATS discovery (Phase 1)")
    parser.add_argument("--limit", type=int, default=0, help="Process only first N employers (0=all)")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()

    global MAX_WORKERS
    MAX_WORKERS = args.workers

    DISCOVERY_DIR.mkdir(parents=True, exist_ok=True)

    employers = load_talent_titans()
    if args.limit > 0:
        employers = employers[:args.limit]
    print(f"Loaded {len(employers)} employers (limit={'all' if args.limit == 0 else args.limit})")

    overlaps = load_protocol_seeds_for_overlap()

    results = []
    with httpx.Client(follow_redirects=True, timeout=TIMEOUT) as client:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_emp = {executor.submit(discover_for_employer, emp, client): emp for emp in employers}
            for i, future in enumerate(as_completed(future_to_emp), 1):
                emp = future_to_emp[future]
                try:
                    res = future.result()
                    results.append(res)
                    if i % 5 == 0:
                        print(f"  processed {i}/{len(employers)}")
                except Exception as e:
                    results.append({"rank": emp.get("rank"), "name": emp.get("name"), "website": emp.get("website"), "error": str(e)[:80]})

    results.sort(key=lambda x: x.get("rank") or 999)

    output_data = {
        "meta": {"source": "talent_titans_top100.yaml", "generated_at": str(date.today()), "total": len(results), "concurrency": MAX_WORKERS},
        "employers": results,
    }
    with open(OUTPUT_YAML, "w") as f:
        yaml.dump(output_data, f, sort_keys=False, allow_unicode=True, width=120)
    print(f"Wrote {OUTPUT_YAML}")

    with open(OUTPUT_RAW_JSON, "w") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    high = [r for r in results if any(c.get("confidence") == "high" and c.get("ats") for c in r.get("careers_candidates", []))]
    print(f"High-confidence ATS in run: {len(high)}")

if __name__ == "__main__":
    main()
