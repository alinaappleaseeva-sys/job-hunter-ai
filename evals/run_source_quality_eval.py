#!/usr/bin/env python3
"""
Targeted quality eval for new sources (web3.career, remote3, findweb3 + existing).

Goal: Collect 20-50 fresh posts, apply negative rules + hard requirements,
compute relevance and ghost rate.

Run:
    PYTHONPATH=src python evals/run_source_quality_eval.py
"""

import json
import re
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from job_hunter_ai.connectors.web3career import Web3CareerConnector
from job_hunter_ai.connectors.remote3 import Remote3Connector
from job_hunter_ai.connectors.findweb3 import FindWeb3Connector
from job_hunter_ai.connectors.cryptojobslist import CryptoJobsListConnector
from job_hunter_ai.normalization.fields.requirements import extract_hard_requirements
from job_hunter_ai.normalization.fields.enrichment import (
    _NEGATIVE_ROLE_PATTERNS,
    infer_role_family,
)
from job_hunter_ai.ghosting.ghosting import compute_ghost_score
from job_hunter_ai.common.models import CanonicalJob

OUTPUT_DIR = Path("evals/runs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NEGATIVE_PATTERNS = _NEGATIVE_ROLE_PATTERNS + [
    re.compile(r"\b(?:intern|internship|junior|jr\.|entry level)\b", re.I),
    re.compile(r"\b(?:marketing|growth|community manager|content|social media)\b", re.I),
    re.compile(r"\b(?:developer|engineer|solidity|frontend|backend|smart contract)\b", re.I),
]

SEGMENT_KEYWORDS = [
    "ops", "operation", "dao", "governance", "treasury", "contributor",
    "program manager", "head of ops", "head of operations", "chief of staff",
    "senior ops", "operations lead", "dao ops",
]

def normalize_record(rec: Any, source: str) -> dict[str, Any]:
    """Turn RawSourceRecord into a simple dict for analysis."""
    payload = getattr(rec, "payload", {}) or {}
    title = (payload.get("title") or getattr(rec, "title", "") or "").strip()
    company = payload.get("company") or "Unknown"
    url = getattr(rec, "source_url", None) or payload.get("url", "")
    desc = payload.get("description") or payload.get("content") or ""

    return {
        "source": source,
        "title": title,
        "company": company,
        "url": url,
        "description": desc[:500] if desc else "",
        "raw": payload,
    }

def passes_negative_rules(text: str) -> tuple[bool, list[str]]:
    """Returns (passes, reasons_if_filtered)"""
    text_lower = text.lower()
    reasons = []
    for pat in NEGATIVE_PATTERNS:
        if pat.search(text_lower):
            reasons.append(f"negative:{pat.pattern[:40]}")
    return len(reasons) == 0, reasons

def has_segment_signal(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in SEGMENT_KEYWORDS)

def make_minimal_canonical(item: dict) -> CanonicalJob:
    """Create a minimal CanonicalJob for ghost scoring."""
    from job_hunter_ai.common.models import CanonicalJob
    title = item["title"]
    return CanonicalJob(
        canonical_job_id=f"{item['source']}-{item.get('url','')[:30]}",
        primary_posting_id=item.get("url", title)[:60],
        company_name=item["company"],
        company_domain=None,
        url=item.get("url", ""),
        title_normalized=title.lower(),
        role_family=infer_role_family(title) or "other",
        seniority="senior" if any(x in title.lower() for x in ["head", "senior", "lead", "manager"]) else "mid",
        market="web3",
        remote_mode="remote",
        employment_type="full-time",
        location_country="Remote",
        location_region=None,
        location_city=None,
        compensation_min=None,
        compensation_max=None,
        compensation_currency="USD",
        canonical_posted_at=datetime.now(UTC),
        source_count=1,
        source_ids=[item["source"]],
    )

def run_eval(target_total: int = 40) -> dict:
    all_posts = []
    sources_used = []

    # 1. web3.career (main target)
    try:
        conn = Web3CareerConnector(paths=["operations-jobs", "dao-jobs"])
        recs = conn.fetch(limit=25).records
        for r in recs:
            item = normalize_record(r, "web3career")
            all_posts.append(item)
        sources_used.append("web3career")
        print(f"web3.career: +{len(recs)}")
    except Exception as e:
        print(f"web3.career error: {e}")

    # 2. remote3
    try:
        conn = Remote3Connector(paths=["/remote-web3-jobs"])
        recs = conn.fetch(limit=15).records
        for r in recs:
            item = normalize_record(r, "remote3")
            all_posts.append(item)
        sources_used.append("remote3")
        print(f"remote3: +{len(recs)}")
    except Exception as e:
        print(f"remote3 error: {e}")

    # 3. findweb3
    try:
        conn = FindWeb3Connector(paths=["/jobs/dao"])
        recs = conn.fetch(limit=10).records
        for r in recs:
            item = normalize_record(r, "findweb3")
            all_posts.append(item)
        sources_used.append("findweb3")
        print(f"findweb3: +{len(recs)}")
    except Exception as e:
        print(f"findweb3 error: {e}")

    # 4. Supplement with cryptojobslist if needed
    if len(all_posts) < target_total:
        try:
            conn = CryptoJobsListConnector()
            recs = conn.fetch(limit=10).records
            for r in recs:
                item = normalize_record(r, "cryptojobslist")
                all_posts.append(item)
            sources_used.append("cryptojobslist")
            print(f"cryptojobslist: +{len(recs)}")
        except Exception as e:
            print(f"cryptojobslist error: {e}")

    # Dedup by title + url
    seen = set()
    unique_posts = []
    for p in all_posts:
        key = (p["title"][:40].lower(), p["url"][:50])
        if key not in seen:
            seen.add(key)
            unique_posts.append(p)

    print(f"\nTotal unique posts collected: {len(unique_posts)}")

    # Analysis
    results = []
    negative_filtered = 0
    hard_cred_mismatch = 0
    segment_relevant = 0
    ghost_scores = []

    for item in unique_posts:
        full_text = f"{item['title']} {item['description']}"
        passes_neg, neg_reasons = passes_negative_rules(full_text)
        if not passes_neg:
            negative_filtered += 1

        hard_reqs = extract_hard_requirements(full_text)
        has_hard_mismatch = hard_reqs.get("requires_accounting_credential", False)

        if has_hard_mismatch:
            hard_cred_mismatch += 1

        seg_signal = has_segment_signal(full_text)
        if seg_signal:
            segment_relevant += 1

        # Ghost score
        try:
            cj = make_minimal_canonical(item)
            gscore, greasons = compute_ghost_score(cj)
        except Exception:
            gscore, greasons = 0.0, ["ghost_calc_failed"]

        ghost_scores.append(gscore)

        passes_all = passes_neg and not has_hard_mismatch and gscore < 0.5

        results.append({
            "source": item["source"],
            "title": item["title"],
            "company": item["company"],
            "url": item["url"],
            "passes_negative": passes_neg,
            "negative_reasons": neg_reasons,
            "hard_requirements": hard_reqs,
            "has_hard_credential_mismatch": has_hard_mismatch,
            "has_segment_signal": seg_signal,
            "ghost_score": gscore,
            "ghost_reasons": greasons,
            "passes_filters": passes_all,
        })

    # Metrics
    total = len(results)
    high_relevance = sum(1 for r in results if r["passes_filters"] and r["has_segment_signal"])
    avg_ghost = sum(ghost_scores) / max(len(ghost_scores), 1)
    high_ghost = sum(1 for s in ghost_scores if s >= 0.4)

    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "total_collected": total,
        "sources": sources_used,
        "metrics": {
            "negative_filter_pass_rate": round((total - negative_filtered) / max(total, 1), 3),
            "negative_filtered_count": negative_filtered,
            "hard_credential_mismatch_count": hard_cred_mismatch,
            "segment_signal_rate": round(segment_relevant / max(total, 1), 3),
            "avg_ghost_score": round(avg_ghost, 3),
            "high_ghost_rate (>=0.4)": round(high_ghost / max(total, 1), 3),
            "high_relevance_count": high_relevance,
            "high_relevance_rate": round(high_relevance / max(total, 1), 3),
        },
        "results": results,
    }

    # Save
    out_file = OUTPUT_DIR / f"source_quality_eval_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "=" * 60)
    print("SOURCE QUALITY EVAL SUMMARY")
    print("=" * 60)
    print(f"Total posts: {total}")
    print(f"Sources: {sources_used}")
    print(f"\nNegative rules pass rate: {report['metrics']['negative_filter_pass_rate']:.1%} (filtered {negative_filtered})")
    print(f"Hard credential mismatch: {hard_cred_mismatch}")
    print(f"Segment signal rate: {report['metrics']['segment_signal_rate']:.1%}")
    print(f"Avg ghost score: {avg_ghost:.3f}")
    print(f"High ghost (>=0.4): {high_ghost} ({report['metrics']['high_ghost_rate (>=0.4)']:.1%})")
    print(f"High relevance (passes filters + segment): {high_relevance} / {total} ({report['metrics']['high_relevance_rate']:.1%})")

    print("\n--- Sample high-relevance ---")
    for r in [x for x in results if x["passes_filters"] and x["has_segment_signal"]][:5]:
        print(f"  [{r['source']}] {r['title'][:55]}")

    print("\n--- Sample filtered by negative ---")
    for r in [x for x in results if not x["passes_negative"]][:3]:
        print(f"  [{r['source']}] {r['title'][:55]} | {r['negative_reasons'][:1]}")

    print(f"\nFull data saved to: {out_file}")
    return report

if __name__ == "__main__":
    run_eval(target_total=40)
