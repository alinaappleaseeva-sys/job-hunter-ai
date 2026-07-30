#!/usr/bin/env python3
"""
Phase 000: Data Preparation for Talent Titans / Best Web3 Employers list.

Usage examples:
    # Generate initial draft from PDF (candidates only)
    python sources/prepare_talent_titans.py --extract

    # Extract + detect overlaps with protocol_seeds + write draft YAML
    python sources/prepare_talent_titans.py --full-draft

    # Enrich a specific slug with discovered careers page (manual step helper)
    python sources/prepare_talent_titans.py --discover --slug aave

    # List overlaps
    python sources/prepare_talent_titans.py --overlaps
"""

import argparse
import subprocess
import re
import yaml
from datetime import date
from pathlib import Path
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Any

PDF_PATH = "/Users/mysmys/Desktop/best web3 employers.pdf"
PROTOCOL_SEEDS = Path(__file__).parent / "protocol_seeds.yaml"
OUTPUT_YAML = Path(__file__).parent / "talent_titans_top100.yaml"
DRAFT_OUTPUT = Path("evals/runs") / "talent_titans_draft.yaml"

COMMON_CAREERS_PATHS = [
    "/careers", "/jobs", "/opportunities", "/open-roles", "/hiring",
    "/about/careers", "/company/careers", "/about/jobs", "/join-us",
]

def extract_from_pdf() -> List[Dict[str, str]]:
    """Extract candidate name + main URL from PDF using pdftotext -layout."""
    result = subprocess.run(
        ["pdftotext", "-layout", PDF_PATH, "-"],
        capture_output=True, text=True
    )
    text = result.stdout

    entries = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        url_match = re.search(r'(https?://[^\s<>"\)\]]+)', line)
        if url_match:
            url = url_match.group(1).rstrip('.,;:)')
            # Look backwards for company name
            name = None
            for j in range(1, 6):
                if i - j < 0:
                    break
                prev = lines[i - j].strip()
                if prev and 3 <= len(prev) <= 55:
                    if not any(bad in prev.lower() for bad in ["superpower", "top", "http"]):
                        if not re.match(r"^\d+\.?$", prev):
                            name = prev.strip(" .:")
                            break
            if not name:
                name = urlparse(url).netloc.replace("www.", "").split(".")[0].title()

            entries.append({"name": name, "main": url})
        i += 1

    # Dedup by domain
    seen = set()
    unique = []
    for e in entries:
        domain = urlparse(e["main"]).netloc.lower()
        if domain and domain not in seen:
            seen.add(domain)
            unique.append(e)
    return unique


def load_protocol_seeds() -> Dict[str, Dict]:
    """Load protocol_seeds for overlap detection."""
    if not PROTOCOL_SEEDS.exists():
        return {}
    with open(PROTOCOL_SEEDS) as f:
        data = yaml.safe_load(f) or {}
    overlaps = {}
    for p in data.get("protocols", []):
        name = p.get("name", "").lower()
        website = p.get("website", "").lower()
        slug = p.get("slug", name.replace(" ", "-"))
        overlaps[slug] = {
            "name": p.get("name"),
            "website": website,
            "slug": slug,
            "has_careers": bool(p.get("careers")),
        }
        # Also index by domain
        if website:
            domain = urlparse(website).netloc.lower()
            overlaps[domain] = overlaps[slug]
    return overlaps


def make_slug(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def discover_careers_pages(main_url: str, max_candidates: int = 5) -> List[str]:
    """Naive discovery: common paths + link hunting on homepage."""
    candidates = []
    try:
        import httpx
        r = httpx.get(main_url, timeout=12, follow_redirects=True,
                      headers={"User-Agent": "talent-titans-prep/0.1"})
        html = r.text if r.status_code < 400 else ""
    except Exception:
        html = ""

    parsed = urlparse(main_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    # Try common paths
    for path in COMMON_CAREERS_PATHS:
        candidate = urljoin(base + "/", path.lstrip("/"))
        if candidate not in candidates:
            candidates.append(candidate)

    # Hunt links in HTML
    if html:
        links = re.findall(r'href=["\']([^"\']*(?:career|job|join|hiring|open-role)[^"\']*)["\']', html, re.I)
        for l in links[:10]:
            full = urljoin(main_url, l)
            if full.startswith("http") and full not in candidates:
                candidates.append(full)

    return candidates[:max_candidates]


def generate_draft(overlaps: Dict) -> Dict:
    """Generate structured draft YAML from PDF extraction + overlap flags."""
    raw = extract_from_pdf()
    draft = {
        "meta": {
            "source": "best web3 employers.pdf",
            "extracted_at": str(date.today()),
            "total_unique": len(raw),
            "note": "This is a draft for Phase 000 enrichment. Fill careers[], ats, priority, ops_relevance manually or via --discover."
        },
        "employers": []
    }

    for item in raw:
        name = item["name"]
        main = item["main"]
        slug = make_slug(name)
        domain = urlparse(main).netloc.lower()

        overlap_info = overlaps.get(slug) or overlaps.get(domain) or {}
        is_overlap = bool(overlap_info)

        entry = {
            "name": name,
            "slug": slug,
            "main": main,
            "careers": [],          # To be filled in enrichment
            "ats": None,            # e.g. {"type": "greenhouse", "board": "aave"} or {"type": "ashby", "org": "li.fi"}
            "priority": "medium",
            "ops_relevance": "unknown",  # high / medium / low / unknown
            "notes": "",
            "overlaps_protocol_seeds": is_overlap,
            "protocol_slug": overlap_info.get("slug") if is_overlap else None,
        }
        draft["employers"].append(entry)

    return draft


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract", action="store_true", help="Just print extracted candidates from PDF")
    parser.add_argument("--full-draft", action="store_true", help="Generate and save draft YAML with overlap flags")
    parser.add_argument("--discover", action="store_true", help="Run discovery for one slug")
    parser.add_argument("--slug", type=str, help="Slug for --discover")
    parser.add_argument("--overlaps", action="store_true", help="Show overlaps with protocol_seeds")
    parser.add_argument("--output", type=str, default=str(OUTPUT_YAML), help="Output path for draft")
    args = parser.parse_args()

    overlaps = load_protocol_seeds()

    if args.extract:
        raw = extract_from_pdf()
        for e in raw[:20]:
            print(f"- {e['name']}: {e['main']}")
        print(f"\nTotal unique: {len(raw)}")
        return

    if args.overlaps:
        raw = extract_from_pdf()
        print("Overlaps with protocol_seeds.yaml:")
        count = 0
        for e in raw:
            domain = urlparse(e["main"]).netloc.lower()
            slug = make_slug(e["name"])
            if slug in overlaps or domain in overlaps:
                info = overlaps.get(slug) or overlaps.get(domain, {})
                print(f"  {e['name']} ({slug}) overlaps with protocol: {info.get('name', info.get('slug'))}")
                count += 1
        print(f"\nFound {count} overlaps.")
        return

    if args.full_draft:
        draft = generate_draft(overlaps)
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            yaml.dump(draft, f, sort_keys=False, allow_unicode=True, width=120)
        print(f"Draft written to {out_path}")
        print(f"Total employers: {len(draft['employers'])}")
        overlaps_count = sum(1 for e in draft["employers"] if e["overlaps_protocol_seeds"])
        print(f"Overlaps detected: {overlaps_count}")
        print("\nNext: manually enrich top 30 (careers URLs, ATS, priority, ops_relevance).")
        return

    if args.discover and args.slug:
        # Find the main URL for this slug in current draft or extract
        raw = extract_from_pdf()
        target = None
        for e in raw:
            if make_slug(e["name"]) == args.slug:
                target = e
                break
        if not target:
            print(f"Slug {args.slug} not found in PDF extraction.")
            return
        print(f"Discovering careers for {target['name']} ({target['main']})...")
        candidates = discover_careers_pages(target["main"])
        for c in candidates:
            print(f"  - {c}")
        print("\nAdd the best one(s) to the YAML under careers:.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
