#!/usr/bin/env python3
"""
Targeted quality eval for sources using the new segment_scorer + per-source thresholds.

Run:
    PYTHONPATH=src python evals/run_source_quality_eval.py
"""

import json
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from job_hunter_ai.connectors.web3career import Web3CareerConnector
from job_hunter_ai.connectors.remote3 import Remote3Connector
from job_hunter_ai.connectors.findweb3 import FindWeb3Connector
from job_hunter_ai.connectors.cryptojobslist import CryptoJobsListConnector
from job_hunter_ai.scoring.segment_scorer import (
    compute_segment_score,
    load_thresholds,
    passes_source_threshold,
)
from job_hunter_ai.normalization.fields.requirements import extract_hard_requirements
from job_hunter_ai.ghosting.ghosting import compute_ghost_score
from job_hunter_ai.common.models import CanonicalJob

OUTPUT_DIR = Path("evals/runs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def normalize_record(rec: Any, source: str) -> dict:
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
        "description": desc[:600] if desc else "",
        "raw": payload,
    }

def make_minimal_canonical(item: dict) -> CanonicalJob:
    from job_hunter_ai.common.models import CanonicalJob
    title = item["title"]
    return CanonicalJob(
        canonical_job_id=f"{item['source']}-{item.get('url','')[:30]}",
        primary_posting_id=item.get("url", title)[:60],
        company_name=item["company"],
        company_domain=None,
        url=item.get("url", ""),
        title_normalized=title.lower(),
        role_family="ops",
        seniority="senior" if any(k in title.lower() for k in ["head", "senior", "lead", "manager"]) else "mid",
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

    # Web3Career
    try:
        conn = Web3CareerConnector(paths=["operations-jobs", "dao-jobs"])
        recs = conn.fetch(limit=25).records
        for r in recs:
            all_posts.append(normalize_record(r, "web3career"))
        sources_used.append("web3career")
        print(f"web3.career: +{len(recs)}")
    except Exception as e:
        print(f"web3.career error: {e}")

    # Remote3
    try:
        conn = Remote3Connector(paths=["/remote-web3-jobs"])
        recs = conn.fetch(limit=15).records
        for r in recs:
            all_posts.append(normalize_record(r, "remote3"))
        sources_used.append("remote3")
        print(f"remote3: +{len(recs)}")
    except Exception as e:
        print(f"remote3 error: {e}")

    # FindWeb3
    try:
        conn = FindWeb3Connector(paths=["/jobs/dao"])
        recs = conn.fetch(limit=10).records
        for r in recs:
            all_posts.append(normalize_record(r, "findweb3"))
        sources_used.append("findweb3")
        print(f"findweb3: +{len(recs)}")
    except Exception as e:
        print(f"findweb3 error: {e}")

    # Dedup
    seen = set()
    unique = []
    for p in all_posts:
        key = (p["title"][:45].lower(), p["url"][:60])
        if key not in seen:
            seen.add(key)
            unique.append(p)

    print(f"\nTotal unique posts collected: {len(unique)}")

    thresholds = load_thresholds()
    print(f"Loaded thresholds: {thresholds}")

    results = []
    negative_filtered = 0
    segment_relevant = 0
    strict_high = 0
    meets_threshold_count = 0
    ghost_scores = []

    for item in unique:
        full_text = f"{item['title']} {item['description']}"
        scoring = compute_segment_score(item["title"], item["description"], item["source"])

        if not any(pat.search(full_text.lower()) for pat in []):  # negatives already in scorer
            pass
        else:
            negative_filtered += 1

        hard_reqs = extract_hard_requirements(full_text)
        has_hard_mismatch = hard_reqs.get("requires_accounting_credential", False)

        seg_signal = scoring["score"] > 0.3 or scoring["has_strong_domain"]
        if seg_signal:
            segment_relevant += 1

        if scoring["passes_strict"]:
            strict_high += 1

        meets_th = passes_source_threshold(scoring["score"], item["source"], thresholds)
        if meets_th:
            meets_threshold_count += 1

        try:
            cj = make_minimal_canonical(item)
            gscore, greasons = compute_ghost_score(cj)
        except Exception:
            gscore, greasons = 0.0, ["ghost_calc_failed"]

        ghost_scores.append(gscore)

        high_relevance = scoring["passes_strict"] and meets_th and gscore < 0.5

        results.append({
            "source": item["source"],
            "title": item["title"],
            "company": item["company"],
            "url": item["url"],
            "scoring": scoring,
            "meets_source_threshold": meets_th,
            "threshold_used": thresholds.get(item["source"].lower(), 0.25),
            "has_segment_signal": seg_signal,
            "ghost_score": gscore,
            "passes_filters": high_relevance,
            "high_relevance_for_source": scoring["passes_strict"] and meets_th,
        })

    total = len(results)
    high_relevance_basic = sum(1 for r in results if r["passes_filters"])

    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "total_collected": total,
        "sources": sources_used,
        "thresholds_used": thresholds,
        "metrics": {
            "segment_signal_rate": round(segment_relevant / max(total, 1), 3),
            "strict_high_quality_count": strict_high,
            "strict_high_quality_rate": round(strict_high / max(total, 1), 3),
            "meets_source_threshold_rate": round(meets_threshold_count / max(total, 1), 3),
            "avg_ghost_score": round(sum(ghost_scores) / max(len(ghost_scores), 1), 3),
            "high_relevance_count": high_relevance_basic,
            "high_relevance_rate": round(high_relevance_basic / max(total, 1), 3),
        },
        "results": results,
    }

    out_file = OUTPUT_DIR / f"source_quality_eval_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 64)
    print("SOURCE QUALITY EVAL (with per-source thresholds + segment_scorer)")
    print("=" * 64)
    print(f"Total posts: {total}")
    print(f"Sources: {sources_used}")
    print(f"Thresholds: {thresholds}")
    print(f"\nStrict high-quality (seniority + domain): {strict_high} ({report['metrics']['strict_high_quality_rate']:.1%})")
    print(f"Meets source threshold: {meets_threshold_count} ({report['metrics']['meets_source_threshold_rate']:.1%})")
    print(f"High relevance (strict + threshold): {high_relevance_basic} / {total} ({report['metrics']['high_relevance_rate']:.1%})")

    print("\n--- Top items that meet their source threshold ---")
    for r in sorted(results, key=lambda x: -x["scoring"]["score"])[:8]:
        if r["meets_source_threshold"]:
            print(f"  [{r['source']}] {r['title'][:55]} | score={r['scoring']['score']} | strict={r['scoring']['passes_strict']}")

    print(f"\nFull data saved to: {out_file}")
    return report

if __name__ == "__main__":
    run_eval()
