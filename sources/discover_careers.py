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


def generate_candidate_slugs(name: str, website: str) -> List[str]:
    """Generate likely ATS slugs from name and website."""
    slugs = set()
    base = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    if base:
        slugs.add(base)
        for suf in ["-labs", "-lab", "-network", "-protocol", "-foundation", "-pbc", "-inc", "-ltd", "-corp"]:
            if base.endswith(suf):
                slugs.add(base[:-len(suf)])
    if website:
        try:
            net = urlparse(website).netloc.lower().replace("www.", "")
            root = net.split(".")[0]
            if root:
                slugs.add(root)
                for suf in ["-labs", "-lab", "-network", "-protocol", "-foundation"]:
                    if root.endswith(suf):
                        slugs.add(root[:-len(suf)])
        except Exception:
            pass
    return list(dict.fromkeys([s for s in slugs if s]))

def probe_known_ats(slugs: List[str]) -> List[str]:
    """Direct ATS slug probes - highest ROI."""
    probes = []
    for s in slugs:
        probes.append(f"https://jobs.ashbyhq.com/{s}")
        probes.append(f"https://job-boards.greenhouse.io/{s}")
        probes.append(f"https://boards.greenhouse.io/{s}")
        probes.append(f"https://jobs.lever.co/{s}")
        probes.append(f"https://apply.workable.com/{s}")
        probes.append(f"https://jobs.workable.com/{s}")
    return probes

def extract_ats_links(html: str, base_url: str) -> List[str]:
    """Light 1-level ATS link harvest from a careers page."""
    if not html:
        return []
    found = set()
    pattern = r'href=["\']([^"\']*(?:jobs\\.ashbyhq\\.com|boards\\.greenhouse\\.io|jobs\\.lever\\.co|apply\\.workable\\.com|jobs\\.workable\\.com)[^"\']*)["\']'
    for m in re.finditer(pattern, html, re.I):
        url = m.group(1)
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            url = urljoin(base_url, url)
        if any(h in url for h in ["ashbyhq.com", "greenhouse.io", "lever.co", "workable.com"]):
            found.add(url)
    return list(found)[:5]

def detect_ats(url: str) -> Optional[Dict[str, str]]:
    """Detect ATS type and board_slug from final URL."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.strip("/")

    if "greenhouse.io" in host:
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


def has_job_signals(html: str, final_url: str, is_ats: bool = False) -> bool:
    """Signal for jobs. Stricter for ATS pages to avoid marketing/404 noise."""
    if not html:
        return False

    text = (html + " " + final_url).lower()
    count = sum(1 for word in JOB_SIGNAL_WORDS if word in text)

    links = re.findall(r'href=["\']([^"\']*(?:job|role|career|apply|hire|position|opening)[^"\']*)["\']', html, re.I)
    link_count = len(links)

    base_ok = (count + link_count) >= 2

    if not is_ats:
        return base_ok

    # For ATS pages require stronger evidence (postings, not just landing)
    strong_indicators = ["position", "role", "opening", "apply now", "/jobs/", "job posting"]
    strong = sum(1 for ind in strong_indicators if ind in text)
    has_structured = ("/job/" in text) or ("apply" in text and link_count >= 1)

    if "workable.com" in final_url:
        # Workable is noisy on unknown slugs - require extra evidence
        return base_ok and strong >= 1 and has_structured

    return base_ok and (strong >= 1 or has_structured)


def check_url(url: str, client: httpx.Client) -> Dict[str, Any]:
    """Perform one check with retries + backoff."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = client.get(url, timeout=TIMEOUT, follow_redirects=True)
            status = resp.status_code
            final_url = str(resp.url)

            ats_info = detect_ats(final_url)
            html = resp.text if status < 400 else ""

            is_real_ats = bool(ats_info) and status == 200

            if status >= 400 and ats_info:
                type_ = "probe_miss"
            elif is_real_ats:
                type_ = "ats"
            elif status == 200:
                type_ = "careers_page"
            else:
                type_ = "error"

            signals = has_job_signals(html, final_url, is_real_ats)

            confidence = "low"
            if is_real_ats and signals:
                confidence = "high"
            elif is_real_ats:
                confidence = "medium"
            elif status == 200 and signals:
                confidence = "medium"

            return {
                "url": final_url,
                "status": status,
                "type": type_,
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


def discover_for_employer(employer: Dict, client: httpx.Client, overlaps_cache: Dict = None) -> Dict[str, Any]:
    name = employer.get("name", "")
    website = employer.get("website", "") or employer.get("main", "")
    rank = employer.get("rank")

    if overlaps_cache is None:
        overlaps_cache = {}

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

    all_results = []
    seen_urls = set()

    # 1. ATS slug probes first (high leverage)
    slugs = generate_candidate_slugs(name, website)
    ats_probes = probe_known_ats(slugs)
    found_strong_ats = False
    for url in ats_probes:
        if url in seen_urls:
            continue
        seen_urls.add(url)
        res = check_url(url, client)
        if (res.get("status") in (200, 301, 302) and res.get("type") != "probe_miss") or (res.get("ats") and res.get("status") == 200):
            all_results.append(res)
            if res.get("ats") and res.get("status") == 200 and res.get("confidence") == "high":
                found_strong_ats = True
                # Early stop for strong ATS to save requests
                break

    # 2. Common paths
    candidates = []
    for path in COMMON_CAREERS_PATHS:
        full = urljoin(base + "/", path.lstrip("/"))
        if full not in seen_urls:
            seen_urls.add(full)
            candidates.append(full)
    if website not in seen_urls:
        seen_urls.add(website)
        candidates.insert(0, website)

    for url in candidates[:12]:
        res = check_url(url, client)
        if res.get("status") in (200, 301, 302) or (res.get("has_job_signals") and res.get("status") < 400):
            all_results.append(res)

    # 3. Light ATS link harvest on any 200 careers pages we already have
    for res in list(all_results):
        if res.get("status") == 200 and not res.get("ats"):
            try:
                # We don't have the html here anymore. Re-fetch lightly only for harvest
                r = client.get(res["url"], timeout=TIMEOUT, follow_redirects=True)
                if r.status_code == 200:
                    harvested = extract_ats_links(r.text, str(r.url))
                    for h in harvested:
                        if h not in seen_urls:
                            seen_urls.add(h)
                            hres = check_url(h, client)
                            if hres.get("ats") or hres.get("status") == 200:
                                all_results.append(hres)
            except Exception:
                pass

    # Dedup by url
    by_url = {}
    for r in all_results:
        u = r.get("url")
        if u and u not in by_url:
            by_url[u] = r
    results = list(by_url.values())

    # Strong priority to ATS high
    def score(r):
        is_ats_200 = bool(r.get("ats")) and r.get("status") == 200
        is_ats = bool(r.get("ats"))
        is_good_status = r.get("status") == 200 or r.get("status") in (301, 302)
        conf = r.get("confidence", "low")

        if is_ats_200:
            return (0, 0)
        if is_ats:
            return (1, 0 if is_good_status else 1)
        if conf == "high":
            return (2, 0 if is_good_status else 1)
        if conf == "medium":
            return (3, 0 if is_good_status else 1)
        return (4, 1)

    results.sort(key=score)

    careers_candidates = results[:8]

    # best_guess: strongly prefer ATS high
    best = None
    for r in results:
        if r.get("ats") and r.get("status") == 200:
            best = {
                "ats": r.get("ats"),
                "board_slug": r.get("board_slug"),
                "careers_url": r.get("url"),
                "confidence": "high",
            }
            break
    if not best:
        for r in results:
            if r.get("confidence") == "high":
                best = {"ats": r.get("ats"), "board_slug": r.get("board_slug"), "careers_url": r.get("url"), "confidence": "high"}
                break
    if not best:
        for r in results:
            if r.get("confidence") == "medium":
                best = {"ats": r.get("ats"), "board_slug": r.get("board_slug"), "careers_url": r.get("url"), "confidence": "medium"}
                break

    already = is_already_in_protocol_seeds(name, website, overlaps_cache)

    return {
        "rank": rank,
        "name": name,
        "website": website,
        "already_in_protocol_seeds": already,
        "careers_candidates": careers_candidates,
        "best_guess": best,
    }



def generate_report(discovery_data: Dict, output_path: Path):
    """Build REPORT.md from real discovery data."""
    employers = discovery_data.get("employers", [])
    total = len(employers)

    high_ats = []
    ats_counts = {"greenhouse": 0, "ashby": 0, "lever": 0, "workable": 0}
    medium = 0
    low_empty = 0
    in_seeds = 0

    top_high = []

    for e in employers:
        cands = e.get("careers_candidates", [])
        has_high_ats = False
        for cand in cands:
            if cand.get("ats") and cand.get("confidence") == "high":
                ats_counts[cand["ats"]] = ats_counts.get(cand["ats"], 0) + 1
                has_high_ats = True
                top_high.append({
                    "rank": e["rank"],
                    "name": e["name"],
                    "ats": cand["ats"],
                    "board_slug": cand.get("board_slug"),
                    "url": cand["url"],
                })
        if has_high_ats:
            high_ats.append(e)
        elif any(c.get("confidence") == "medium" for c in cands):
            medium += 1
        else:
            low_empty += 1

        if e.get("already_in_protocol_seeds"):
            in_seeds += 1

    top_high.sort(key=lambda x: x["rank"])
    top_high = top_high[:15]

    lines = []
    lines.append("# Talent Titans ATS Discovery Report")
    lines.append("")
    lines.append(f"**Generated**: {discovery_data['meta'].get('generated_at', 'unknown')} (from real data)")
    lines.append(f"**Total employers processed**: {total}")
    lines.append(f"**Concurrency**: {discovery_data['meta'].get('concurrency', 3)}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- High-confidence ATS: {len(high_ats)}")
    lines.append(f"- Medium confidence (no ATS): {medium}")
    lines.append(f"- Low / empty: {low_empty}")
    lines.append(f"- Already in protocol_seeds: {in_seeds}")
    lines.append("")
    lines.append("## ATS Breakdown")
    for k, v in ats_counts.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Top High-Confidence ATS")
    if top_high:
        for i, item in enumerate(top_high, 1):
            lines.append(f"{i}. {item['name']} (rank {item['rank']}) — {item['ats']} / {item['board_slug']} — {item['url']}")
    else:
        lines.append("(none in this run)")
    lines.append("")
    lines.append("## Notes")
    lines.append("- Run with `--limit` + resume for full 100.")
    lines.append("- best_guess prioritizes direct ATS hits as high.")
    lines.append("")
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Wrote {output_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Talent Titans career/ATS discovery (Phase 1.1 - ATS-first)")
    parser.add_argument("--limit", type=int, default=0, help="Process only first N employers (0=all)")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--resume", action="store_true", help="Skip ranks already present in discovery yaml")
    args = parser.parse_args()

    global MAX_WORKERS
    MAX_WORKERS = args.workers

    DISCOVERY_DIR.mkdir(parents=True, exist_ok=True)

    all_employers = load_talent_titans()

    # Resume support
    processed_ranks = set()
    existing_results = []
    if args.resume and OUTPUT_YAML.exists():
        try:
            old = yaml.safe_load(open(OUTPUT_YAML)) or {}
            for e in old.get("employers", []):
                if e.get("rank") is not None:
                    processed_ranks.add(e["rank"])
                    existing_results.append(e)
            print(f"Resume: skipping {len(processed_ranks)} already processed ranks")
        except Exception as ex:
            print(f"Resume load warning: {ex}")

    overlaps_cache = load_protocol_seeds_for_overlap()

    employers = [e for e in all_employers if e.get("rank") not in processed_ranks]
    if args.limit > 0:
        employers = employers[:args.limit]
    print(f"Loaded {len(employers)} employers to process (limit={'all' if args.limit == 0 else args.limit})")

    if not employers:
        print("Nothing new to process.")
        if OUTPUT_YAML.exists():
            data = yaml.safe_load(open(OUTPUT_YAML)) or {}
            generate_report(data, Path("sources/discovery/REPORT.md"))
        return

    results = list(existing_results)

    with httpx.Client(follow_redirects=True, timeout=TIMEOUT) as client:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_emp = {executor.submit(discover_for_employer, emp, client, overlaps_cache): emp for emp in employers}
            for i, future in enumerate(as_completed(future_to_emp), 1):
                emp = future_to_emp[future]
                try:
                    res = future.result()
                    results.append(res)
                    if i % 5 == 0 or i == len(employers):
                        print(f"  processed {i}/{len(employers)}")
                        # Flush every 5
                        if len(results) % 5 == 0:
                            tmp = {"meta": {"source": "talent_titans_top100.yaml", "generated_at": str(date.today()), "total": len(results), "concurrency": MAX_WORKERS}, "employers": sorted(results, key=lambda x: x.get("rank") or 999)}
                            with open(OUTPUT_YAML, "w") as f:
                                yaml.dump(tmp, f, sort_keys=False, allow_unicode=True, width=120)
                            print("  (flushed partial)")
                except Exception as e:
                    results.append({"rank": emp.get("rank"), "name": emp.get("name"), "website": emp.get("website"), "error": str(e)[:80]})

    results = sorted(results, key=lambda x: x.get("rank") or 999)

    output_data = {
        "meta": {"source": "talent_titans_top100.yaml", "generated_at": str(date.today()), "total": len(results), "concurrency": MAX_WORKERS},
        "employers": results,
    }
    with open(OUTPUT_YAML, "w") as f:
        yaml.dump(output_data, f, sort_keys=False, allow_unicode=True, width=120)
    print(f"Wrote {OUTPUT_YAML}")

    with open(OUTPUT_RAW_JSON, "w") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    # Auto-generate REPORT from real data
    generate_report(output_data, Path("sources/discovery/REPORT.md"))

    high_count = sum(1 for r in results if any(c.get("confidence") == "high" and c.get("ats") for c in r.get("careers_candidates", [])))
    print(f"High-confidence ATS found: {high_count}")

if __name__ == "__main__":
    main()
