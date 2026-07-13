#!/usr/bin/env python3
"""
Autonomous Cycle runner (Phase 4 foundation).

Runs the full job-hunter pipeline on Alina profile, applies ranking/ghost,
generates HTML report, and emits telemetry.

Usage:
    python scripts/autonomous_cycle.py --limit 6

Outputs:
- job_results.html (updated)
- telemetry JSON with raw/ranked counts, top titles, per-source, errors

Designed for cron / Hermes agent loops.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Make src importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from job_hunter_ai.pipeline import run_full_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("autonomous_cycle")

REPORT_PATH = Path("job_results.html")
TELEMETRY_DIR = Path("reports")
TELEMETRY_DIR.mkdir(exist_ok=True)


def main(limit: int = 6) -> dict:
    logger.info("=== Starting autonomous cycle (Phase 4) ===")

    start = datetime.utcnow()
    result = run_full_pipeline(limit_per_source=limit)

    ranked = result.get("ranked_jobs", [])
    metrics = result.get("metrics", {})

    # Telemetry
    top_jobs = []
    for r in ranked[:5]:
        cj = r.canonical_job
        bd = getattr(r, "score_breakdown", None)
        top_jobs.append({
            "title": cj.title_normalized,
            "company": cj.company_name,
            "score": round(bd.total_score, 3) if bd else None,
            "role_family": cj.role_family,
            "market": cj.market,
            "url": cj.url,
            "comp_min": cj.compensation_min,
        })

    telemetry = {
        "timestamp": start.isoformat() + "Z",
        "profile_id": result["profile"].profile_id,
        "raw_count": result["total_raw"],
        "ranked_count": len(ranked),
        "sources": result["sources"],
        "metrics": metrics,
        "top_5": top_jobs,
        "duration_seconds": (datetime.utcnow() - start).total_seconds(),
    }

    # Write telemetry
    ts = start.strftime("%Y%m%d_%H%M%S")
    telemetry_path = TELEMETRY_DIR / f"telemetry_{ts}.json"
    with open(telemetry_path, "w") as f:
        json.dump(telemetry, f, indent=2)

    logger.info(f"Telemetry: raw={telemetry['raw_count']}, ranked={telemetry['ranked_count']}, target_ratio={metrics.get('target_role_ratio')}")
    logger.info(f"Top titles: {[t['title'][:50] for t in top_jobs]}")
    logger.info(f"Telemetry saved to {telemetry_path}")

    # Regenerate report (re-uses pipeline run)
    # Regenerate fresh HTML report
    try:
        import subprocess
        subprocess.check_call([sys.executable, "demo/generate_html_report.py"], cwd=Path(__file__).parent.parent)
    except Exception as e:
        logger.warning(f"Report generation skipped: {e}")

    logger.info("=== Cycle complete ===")
    return telemetry


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=6, help="limit per source")
    args = parser.parse_args()
    main(limit=args.limit)
