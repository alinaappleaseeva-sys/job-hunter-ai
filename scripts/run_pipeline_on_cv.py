#!/usr/bin/env python3
"""
End-to-end pipeline runner for Phase 10 demo.

Uses Alina Aseeva's real CV (Head of Operations, Web3/DAO/DeFi focus)
to build a CandidateProfile, fetches live jobs from RemoteOK,
runs ranking + ghosting, and produces a delivery digest.

Run:
    python scripts/run_pipeline_on_cv.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from typing import Any

# Ensure we can import the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from job_hunter_ai.common.models import (
    CanonicalJob,
    CandidateProfile,
    JobScoreBreakdown,
    RankedJob,
)
from job_hunter_ai.connectors.remoteok import RemoteOKConnector
from job_hunter_ai.delivery import build_digest, apply_action
from job_hunter_ai.ghosting.ghosting import (
    apply_ghost_penalty,
    compute_ghost_score,
)
from job_hunter_ai.ranking.ranking import rank_jobs


def build_profile_from_alina_cv() -> CandidateProfile:
    """Hand-crafted profile derived from the attached real CV."""
    return CandidateProfile(
        profile_id="alina-aseeva-head-ops-web3",
        target_role_families=["operations", "program_management", "head_of_ops", "dao_ops"],
        target_seniorities=["head", "lead", "senior"],
        target_title_keywords=[
            "operations", "program", "head of", "dao", "governance",
            "project management", "ops lead", "web3 ops",
        ],
        remote_preference="remote",
        preferred_locations=["remote", "any"],
        min_compensation=140000,
        compensation_currency="USD",
        preferred_markets=["web3", "defi", "dao", "crypto", "blockchain"],
        notes=(
            "10+ years building ops from scratch in Web3/DAO/DeFi. "
            "Strong on governance, cross-functional alignment, AI automation, "
            "treasury/settlement, and scaling operations. Returning to full-time in 2026."
        ),
    )


def remoteok_to_canonical_jobs(limit: int = 25) -> list[CanonicalJob]:
    """Fetch live from RemoteOK and convert to minimal CanonicalJob."""
    conn = RemoteOKConnector()
    result = conn.fetch(limit=limit)
    jobs: list[CanonicalJob] = []

    for rec in result.records:
        payload = rec.payload or {}
        title = payload.get("position") or payload.get("title") or "Unknown Role"
        company = payload.get("company") or "Unknown Company"
        location = payload.get("location") or "Remote"
        tags = payload.get("tags", []) or []
        salary = payload.get("salary") or ""

        # Very lightweight mapping
        market = "web3" if any(t.lower() in ("crypto", "web3", "blockchain", "defi", "dao") for t in tags) else "saas"

        cj = CanonicalJob(
            canonical_job_id=f"remoteok-{rec.external_id}",
            primary_posting_id=rec.external_id,
            company_name=company,
            company_domain=None,
            title_normalized=title.lower(),
            role_family="operations" if any(k in title.lower() for k in ["ops", "operations", "program"]) else "engineering",
            seniority="senior" if "senior" in title.lower() or "lead" in title.lower() else "mid",
            market=market,
            remote_mode="remote",
            employment_type="full-time",
            location_country="Remote",
            location_region=None,
            location_city=None,
            compensation_min=150000 if "150" in salary or "160" in salary else 120000,
            compensation_max=None,
            compensation_currency="USD",
            canonical_posted_at=rec.discovered_at or datetime.utcnow(),
            first_seen_at=rec.fetched_at,
            last_seen_at=rec.fetched_at,
            active_posting_count=1,
            source_count=1,
            ghost_score=None,
            canonical_status="active",
            merge_confidence=0.8,
            merge_reasons=["remoteok-direct"],
        )
        jobs.append(cj)
    return jobs


def main() -> None:
    print("=== Phase 10 Pipeline on Real CV (Alina Aseeva) ===\n")

    profile = build_profile_from_alina_cv()
    print(f"Profile: {profile.profile_id}")
    print(f"Target families: {profile.target_role_families}")
    print(f"Markets: {profile.preferred_markets}")
    print(f"Remote pref: {profile.remote_preference}\n")

    print("Fetching live jobs from RemoteOK...")
    try:
        canonical_jobs = remoteok_to_canonical_jobs(limit=20)
        print(f"Fetched {len(canonical_jobs)} jobs\n")
    except Exception as e:
        print(f"RemoteOK fetch failed ({e}). Using synthetic fallback jobs.\n")
        canonical_jobs = _make_synthetic_jobs()

    print("Running ranking...")
    ranked = rank_jobs(profile, canonical_jobs)
    print(f"Ranked {len(ranked)} jobs.\n")

    print("Applying ghost penalty...")
    apply_ghost_penalty(ranked)  # mutates in place with downrank
    print("Ghosting complete.\n")

    print("Building delivery digest...")
    digest = build_digest(profile, ranked, limit=8)

    print("\n" + "=" * 60)
    print("TOP MATCHES FOR ALINA ASEEVA (Head of Operations, Web3)")
    print("=" * 60 + "\n")

    for item in digest["jobs"][:8]:
        print(f"#{item.get('rank', '?')} {item['title']} @ {item['company']}")
        print(f"   Score: {item['total_score']:.2f} | Ghost: {item.get('ghost_score', 0):.2f}")
        print(f"   Explanations:")
        for exp in item.get("explanations", [])[:3]:
            print(f"     - {exp['component']}: {exp['score']:.2f} ({', '.join(exp.get('reasons', []))})")
        print()

    # Example structured feedback (as if user reviewed)
    if ranked:
        print("--- Example structured feedback ---")
        top = ranked[0]
        event = apply_action(top, profile.profile_id, "relevant", "Strong Web3 ops alignment + remote")
        print(f"Action recorded: {event.action} on {event.canonical_job_id}")
        print(f"Trace: total_score={event.score_breakdown.total_score:.2f}, ghost={event.ghost_score}")

    print("\nPipeline run complete.")


def _make_synthetic_jobs() -> list[CanonicalJob]:
    """Realistic Web3/Ops jobs matching Alina profile for demo."""
    base = datetime.utcnow()
    jobs = []
    samples = [
        ("Head of Operations - Web3 Protocol", "StableUnit DAO", "operations", "head", "web3", 165000),
        ("Program Manager, DAO Governance", "Arbitrum Foundation", "operations", "senior", "web3", 155000),
        ("Operations Lead - DeFi", "Lido", "operations", "lead", "defi", 180000),
        ("Head of DAO Operations", "Aave", "operations", "head", "defi", 190000),
        ("Governance & Ops Manager", "ENS DAO", "operations", "senior", "dao", 145000),
    ]
    for i, (title, company, role, sen, market, comp) in enumerate(samples):
        jobs.append(CanonicalJob(
            canonical_job_id=f"synthetic-{i}",
            primary_posting_id=f"p{i}",
            company_name=company,
            company_domain=None,
            title_normalized=title.lower(),
            role_family=role,
            seniority=sen,
            market=market,
            remote_mode="remote",
            employment_type="full-time",
            location_country="Remote",
            location_region=None,
            location_city=None,
            compensation_min=comp,
            compensation_max=None,
            compensation_currency="USD",
            canonical_posted_at=base - timedelta(days=i),
            first_seen_at=base,
            last_seen_at=base,
            active_posting_count=1,
            source_count=1,
            ghost_score=None,
            canonical_status="active",
            merge_confidence=0.7,
            merge_reasons=["synthetic"],
        ))
    return jobs


if __name__ == "__main__":
    main()
