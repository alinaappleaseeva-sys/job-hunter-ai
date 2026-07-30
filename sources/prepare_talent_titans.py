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

PDF_PATH = None  # will be resolved below

def get_pdf_path() -> str:
    """Resolve PDF path. Priority: env var > relative to this file > original desktop location (dev only)."""
    import os
    if os.environ.get("TALENT_TITANS_PDF"):
        return os.environ["TALENT_TITANS_PDF"]
    # Try relative to sources/
    candidate = Path(__file__).parent / "best web3 employers.pdf"
    if candidate.exists():
        return str(candidate)
    # Fallback for local dev (the PDF lives outside repo)
    desktop = "/Users/mysmys/Desktop/best web3 employers.pdf"
    if Path(desktop).exists():
        return desktop
    raise FileNotFoundError(
        "PDF not found. Set TALENT_TITANS_PDF env var or place the PDF next to this script."
    )

# Use get_pdf_path() in extract_from_pdf instead of direct PDF_PATH
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
        ["pdftotext", "-raw", get_pdf_path(), "-"],
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
                "name": clean_name(name),
                "website": url,
                "superpower": clean_superpower(superpower),
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
    """Load protocol_seeds for overlap detection.
    Now also stores normalized domains for fuzzy matching.
    """
    if not PROTOCOL_SEEDS.exists():
        return {}
    with open(PROTOCOL_SEEDS) as f:
        data = yaml.safe_load(f) or {}
    overlaps = {}
    for p in data.get("protocols", []):
        name = p.get("name", "")
        website = p.get("website", "").lower()
        slug = p.get("slug", make_slug(name))
        
        entry = {
            "name": name,
            "website": website,
            "slug": slug,
            "has_careers": bool(p.get("careers")),
            "domains": set(),
        }
        
        if website:
            netloc = urlparse(website).netloc.lower().replace("www.", "")
            entry["domains"].add(netloc)
            # Add parent domain for fuzzy match (e.g. uniswap.org from app.uniswap.org)
            parts = netloc.split(".")
            if len(parts) > 2:
                entry["domains"].add(".".join(parts[-2:]))
        
        overlaps[slug] = entry
        # index by main domain too
        for d in list(entry["domains"]):
            overlaps[d] = entry
            
    return overlaps




def is_overlap_with_seeds(name: str, website: str, overlaps: Dict) -> tuple:
    """Return (is_overlap, protocol_slug) with better fuzzy matching."""
    slug = make_slug(name)
    if slug in overlaps:
        return True, overlaps[slug].get("slug", slug)
    
    if not website:
        return False, None
    try:
        netloc = urlparse(website).netloc.lower().replace("www.", "")
        domain = ".".join(netloc.split(".")[-2:])
    except Exception:
        domain = ""
    
    for key, info in overlaps.items():
        if key == slug:
            return True, info.get("slug", slug)
        if domain and any(d in domain or domain in d for d in info.get("domains", set())):
            return True, info.get("slug", slug)
        if name.lower() in info.get("name", "").lower() or info.get("name", "").lower() in name.lower():
            return True, info.get("slug", slug)
    return False, None

def make_slug(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def clean_name(name: str) -> str:
    """Fix common PDF extraction artifacts in company names."""
    name = name.strip()
    # Fix "T rust Wallet" → "Trust Wallet", "T o unlock" style
    name = re.sub(r"T\s+([a-z])", r"T", name, flags=re.I)
    name = re.sub(r"([A-Z])\s+([a-z])", r"", name)  # "Internet of T rust"
    name = re.sub(r"\s+", " ", name)
    return name.strip()

def clean_superpower(text: str, next_name: str = "") -> str:
    """Remove stuck neighboring company names and normalize whitespace from -raw."""
    if not text:
        return ""
    # Remove common stuck suffixes that are other company names
    stuck_patterns = [
        r"\s+Sei Network\s*$",
        r"\s+Solana\s*$",
        r"\s+Puffer\s*$",
        r"\s+Compound\s*$",
    ]
    for pat in stuck_patterns:
        text = re.sub(pat, "", text, flags=re.I)
    
    # Fix glued words: Alchemyiscreating → Alchemy is creating
    text = re.sub(r"([a-z])([A-Z])", r" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


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
        name = clean_name(item["name"])
        website = item.get("website") or item.get("main", "")
        rank = item.get("rank", 0)
        superpower = clean_superpower(item.get("superpower", ""))
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
            w = e.get("website") or e.get("main", "")
            print(f"- {e.get('rank', '?')}. {e['name']}: {w}")
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
        main_url = target.get("website") or target.get("main", "")
        candidates = discover_careers_pages(main_url)
        for c in candidates:
            print(f"  - {c}")
        print("\nAdd the best one(s) to the YAML under careers:.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
