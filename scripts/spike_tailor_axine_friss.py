#!/usr/bin/env python3
"""
Vertical Spike: Tailor CV for Axine Labs + Friss Labs
Fast Phase 0 (parser + fact library) + initial Phase 1+2.

Usage:
    python scripts/spike_tailor_axine_friss.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import json
import hashlib
from datetime import datetime
from typing import List

from cv_tailor.models import MasterCV, JobRequirement, Gap
from cv_tailor.parser import parse_master_cv

MASTER_CV_PATH = Path("docs/Alina_Aseeva_CV_14.07.2026.md")

# === Realistic placeholder JDs for the spike ===
# Replace these with exact job descriptions when you have them.

AXINE_JD = JobRequirement(
    job_id="axine-labs-head-of-operations-2026",
    title="Head of Operations",
    company="Axine Labs",
    url="https://wellfound.com/company/axine-labs/jobs",
    must_have=[
        "Build and run operations from 0 to 1 in a startup",
        "Cross-functional leadership across product, engineering, legal, finance",
        "Strong execution, process design and stakeholder alignment",
        "Web3 / crypto / DAO experience is a significant plus",
    ],
    nice_to_have=[
        "Treasury management or capital allocation experience",
        "Experience working with DAOs or decentralized teams",
        "Using AI/automation to drive operational efficiency",
    ],
    keywords=["operations", "web3", "dao", "cross-functional", "execution", "treasury", "startup", "process"],
    level="head",
    raw_description="Head of Operations role at Axine Labs. Own end-to-end operations in a fast-moving Web3 company. Align engineering, product and GTM. Design processes and drive execution from 0 to 1.",
)

FRISS_JD = JobRequirement(
    job_id="friss-labs-dao-operations-pm-2026",
    title="Program Manager, DAO Operations",
    company="Friss Labs",
    url=None,
    must_have=[
        "Hands-on DAO governance and operations experience",
        "Program management across multiple workstreams and contributors",
        "Contributor coordination and async remote team operations",
        "Strong written communication for proposals and updates",
    ],
    nice_to_have=[
        "Treasury oversight or token governance experience",
        "Previous work in DAO tooling or contributor management platforms",
    ],
    keywords=["dao", "governance", "program manager", "operations", "web3", "contributors", "async", "proposal"],
    level="senior",
    raw_description="Program Manager for DAO Operations at Friss Labs. Coordinate governance, manage contributor programs, run working groups, and drive execution in a fully remote Web3 environment.",
)


def basic_gap_analysis(master: MasterCV, job: JobRequirement) -> List[Gap]:
    """Naive keyword gap detection for the spike."""
    gaps: List[Gap] = []
    all_master_text = " ".join(
        [e.title + " " + " ".join([b.text for b in e.bullets]) for e in master.experiences]
    ).lower()

    for must in job.must_have:
        terms = [t for t in must.lower().split() if len(t) > 4]
        found = any(t in all_master_text for t in terms)
        if not found:
            gaps.append(Gap(
                category="must_have",
                description=must,
                evidence_in_master=[],
                missing_signals=[must]
            ))
    return gaps


def main():
    print("=== Vertical Spike: Axine Labs + Friss Labs ===\n")

    raw = MASTER_CV_PATH.read_text()
    master = parse_master_cv(raw)

    print(f"Master CV version: {master.version}")
    print(f"Parsed experiences: {len(master.experiences)}")
    print()

    jobs = [AXINE_JD, FRISS_JD]

    results = []

    for job in jobs:
        print(f"### {job.title} @ {job.company}")
        gaps = basic_gap_analysis(master, job)
        print(f"Naive gaps detected: {len(gaps)}")
        for g in gaps:
            print(f"  • {g.description}")

        # Minimal tailoring output (will improve in real Phase 2)
        tailored = {
            "summary": master.summary[:300] + "...",
            "note": "This is a placeholder. Real rephrasing + reordering will come next."
        }
        print(f"Tailored summary (stub): {tailored['summary'][:150]}...\n")

        results.append({
            "job_id": job.job_id,
            "title": job.title,
            "company": job.company,
            "gaps": [g.model_dump() for g in gaps],
            "tailored_stub": tailored,
        })

    # Save results
    output = {
        "master_cv_version": master.version,
        "timestamp": datetime.now().isoformat(),
        "jobs": results,
    }
    out_path = Path("spike_results_axine_friss.json")
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Saved results → {out_path}")
    print("\n--- Ready for Discovery Session ---")
    print("Please review the gaps above. I will now ask targeted questions.")


if __name__ == "__main__":
    main()
