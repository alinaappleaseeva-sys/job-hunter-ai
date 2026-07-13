#!/usr/bin/env python3
"""
Lightweight Precision@K eval for Phase 5+.

Uses target_role_family + existing gold as proxy for relevance.
Reports precision on top-k for target titles (Head of Ops / CoS focus).

Run:
    python evals/harness/precision_topk.py --k 10
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from job_hunter_ai.pipeline import run_full_pipeline, get_alina_profile


def main(k: int = 10):
    profile = get_alina_profile()
    result = run_full_pipeline(limit_per_source=8)
    ranked = result["ranked_jobs"]
    raw = result["total_raw"]

    top_k = ranked[:k]

    # Proxy relevance: role_family in target or high score
    target_families = set(profile.target_role_families)
    relevant = 0
    for rj in top_k:
        cj = rj.canonical_job
        if cj.role_family in target_families or rj.score_breakdown.total_score >= 0.85:
            relevant += 1

    precision = relevant / k
    target_ratio_raw = result["metrics"].get("target_role_ratio", 0)

    print(f"Precision@{k}: {precision:.3f} ({relevant}/{k})")
    print(f"Raw target role ratio: {target_ratio_raw}")
    print(f"Total raw: {raw}")
    print("Gate: precision@10 >= 0.70 (proxy) ? ", "PASS" if precision >= 0.70 else "WARN")

    if precision < 0.60:
        print("WARNING: precision below baseline — review top results.")
        return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=10)
    args = parser.parse_args()
    sys.exit(main(args.k))
