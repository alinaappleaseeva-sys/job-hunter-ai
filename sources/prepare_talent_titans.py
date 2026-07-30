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

def extract_from_pdf() -> List[Dict[str, Any]]:
    """Extract rank, name, website, superpower from PDF using pdftotext -raw (layout-independent)."""
    result = subprocess.run(
        ["pdftotext", "-raw", PDF_PATH, "-"],
        capture_output=True, text=True
    )
    text = result.stdout
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    url_to_info: Dict[str, Dict] = {}
    for idx, line in enumerate(lines):
        if not line.startswith("http"):
            continue
        url = line
        rank = None
        name = None
        for k in range(1, 6):
            if idx - k < 0:
                break
            prev = lines[idx - k]
            m = re.match(r"^(\d{1,3})\.\s*(.+)$", prev)
            if m:
                rank = int(m.group(1))
                name = m.group(2).strip()
                break
            m2 = re.match(r"^(\d{1,3})\.?$", prev)
            if m2:
                rank = int(m2.group(1))
                if idx - k - 1 >= 0:
                    name_cand = lines[idx - k - 1]
                    if (not name_cand.startswith("http") and "Superpower" not in name_cand
                            and len(name_cand) > 2 and not re.match(r"^\d", name_cand)):
                        name = name_cand.strip()
                        break
                break
            if (not name and not re.match(r"^\d", prev) and not prev.startswith("http")
                    and "Superpower" not in prev and "Top" not in prev and "Employers" not in prev
                    and len(prev) > 3 and len(prev) < 50):
                name = prev.strip()
                if idx - k - 1 >= 0:
                    m3 = re.match(r"^(\d{1,3})\.?", lines[idx - k - 1])
                    if m3:
                        rank = int(m3.group(1))
                break

        superpower = ""
        for k in range(1, 8):
            if idx + k >= len(lines):
                break
            nextl = lines[idx + k]
            if nextl.startswith("http") or re.match(r"^\d{1,3}\.?\s*$", nextl):
                break
            if "Superpower:" in nextl:
                superpower = re.sub(r".*Superpower:\s*", "", nextl).strip()
                for m in range(1, 6):
                    if idx + k + m >= len(lines):
                        break
                    nl = lines[idx + k + m]
                    if (nl.startswith("http") or re.match(r"^\d{1,3}\.", nl)
                            or re.match(r"^\d{1,3}$", nl) or "Superpower" in nl):
                        break
                    if nl and not nl.startswith("Top") and "Employers" not in nl and len(nl) > 5:
                        superpower += " " + nl
                break

        if url and name:
            url_to_info[url] = {
                "rank": rank or 0,
                "name": name.strip(" .:"),
                "website": url,
                "superpower": superpower.strip(),
            }

    # fix Sei etc.
    for e in url_to_info.values():
        if e["name"] == "Sei Network" and e["rank"] == 0:
            e["rank"] = 16

    # dedup by rank, prefer richer superpower
    by_rank: Dict[int, Dict] = {}
    for e in url_to_info.values():
        r = e.get("rank") or 0
        if r and (r not in by_rank or len(by_rank[r].get("superpower", "")) < len(e.get("superpower", ""))):
            by_rank[r] = e

    unique = sorted([e for e in by_rank.values() if e.get("rank")], key=lambda x: x["rank"])
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
    """Generate structured draft YAML from PDF extraction + overlap flags.
    Structure: rank + name + website + superpower (from PDF, source of truth) + enrichment slots.
    """
    raw = extract_from_pdf()
    draft = {
        "meta": {
            "source": "best web3 employers.pdf",
            "extracted_at": str(date.today()),
            "total_unique": len(raw),
            "note": "Source of truth from PDF (Phase 0). careers/ats/priority/ops_relevance to be enriched via discovery or manual. Discovery results go to separate discovery/ file."
        },
        "employers": []
    }

    for item in raw:
        name = item["name"]
        website = item.get("website") or item.get("main", "")
        rank = item.get("rank", 0)
        superpower = item.get("superpower", "")
        slug = make_slug(name)
        domain = urlparse(website).netloc.lower()

        overlap_info = overlaps.get(slug) or overlaps.get(domain) or {}
        is_overlap = bool(overlap_info)

        entry = {
            "rank": rank,
            "name": name,
            "website": website,
            "superpower": superpower,
            "slug": slug,
            "careers": [],          # To be filled in Phase 1/2
            "ats": None,            # e.g. {"type": "greenhouse", "board": "..."}
            "priority": "medium",
            "ops_relevance": "unknown",
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
            domain = urlparse(e.get("website") or e.get("main")).netloc.lower()
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
        print(f"Discovering careers for {target['name']} ({target.get('website') or target.get('main')})...")
        candidates = discover_careers_pages(target["main"])
        for c in candidates:
            print(f"  - {c}")
        print("\nAdd the best one(s) to the YAML under careers:.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
