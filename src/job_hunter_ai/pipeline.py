"""Core pipeline for job aggregation and ranking (Phase 0 foundations).

Provides:
- get_alina_profile()
- fetch_all_wave1()
- run_full_pipeline()
- Basic metrics and telemetry for self-validation.

Follows repo principles: explicit, testable, with fallbacks.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from job_hunter_ai.common.models import CanonicalJob, CandidateProfile
from job_hunter_ai.connectors.arcdev import ArcDevConnector
from job_hunter_ai.connectors.remoteok import RemoteOKConnector
from job_hunter_ai.connectors.telegram import TelegramConnector
from job_hunter_ai.connectors.weworkremotely import WeWorkRemotelyConnector
from job_hunter_ai.connectors.wellfound import WellfoundConnector
from job_hunter_ai.connectors.workable import WorkableConnector
from job_hunter_ai.delivery import build_digest
from job_hunter_ai.ghosting.ghosting import apply_ghost_penalty
from job_hunter_ai.ranking.ranking import rank_jobs

logger = logging.getLogger(__name__)


def get_alina_profile() -> CandidateProfile:
    """Single source of truth for Alina's profile (Head of Ops / CoS, Web3 focus) - Phase 0/1 baseline."""
    return CandidateProfile(
        profile_id="alina-aseeva-head-ops-web3",
        target_role_families=["operations", "program_management", "head_of_ops", "dao_ops", "chief_of_staff"],
        target_seniorities=["head", "lead", "senior", "chief"],
        target_title_keywords=[
            "operations", "program", "head of", "dao", "governance",
            "project management", "ops lead", "web3 ops", "program manager",
            "chief of staff", "head of operations", "chief of", "ops manager",
        ],
        remote_preference="remote",
        preferred_locations=["remote", "any"],
        min_compensation=120000,
        compensation_currency="USD",
        preferred_markets=["web3", "defi", "dao", "crypto", "blockchain", "fintech"],
        notes="10+ years building ops from scratch in Web3/DAO/DeFi. Strong on governance, treasury, cross-functional alignment, AI automation. Returning to full-time in 2026.",
    )


def _to_canonical(rec: Any, source: str) -> CanonicalJob | None:
    payload = rec.payload or {}
    title = (payload.get("title") or payload.get("position") or "").strip()
    if not title:
        return None

    company = payload.get("company") or payload.get("company_name") or "Unknown"

    url = (
        getattr(rec, "source_url", None)
        or payload.get("url")
        or payload.get("application_url")
        or payload.get("link")
        or payload.get("absolute_url")
    )

    title_lower = title.lower()

    market_keywords = ["web3", "crypto", "defi", "dao", "blockchain", "fintech"]
    market = "web3" if any(k in title_lower for k in market_keywords) else "saas"

    ops_keywords = ["ops", "operations", "program", "governance", "head of", "dao", "chief of staff", "head of operations"]
    role_family = "operations" if any(k in title_lower for k in ops_keywords) else "other"

    seniority = "senior" if any(k in title_lower for k in ["senior", "lead", "head", "manager", "chief"]) else "mid"

    comp_min = None
    salary = str(payload.get("salary") or payload.get("compensation") or payload.get("salary_range") or "")
    salary_lower = salary.lower()
    for num in ["160", "150", "180", "170", "140", "130", "120", "110"]:
        if num in salary_lower:
            comp_min = int(num) * 1000
            break
    if comp_min is None:
        content = str(payload.get("content") or payload.get("description") or "")
        import re
        m = re.search(r'\$?\s*(\d{2,3})\s*[kK]', content)
        if m:
            val = int(m.group(1))
            if val >= 100:
                comp_min = val * 1000

    return CanonicalJob(
        canonical_job_id=f"{source}-{rec.external_id}",
        primary_posting_id=rec.external_id,
        company_name=company,
        company_domain=None,
        url=url,
        title_normalized=title.lower(),
        role_family=role_family,
        seniority=seniority,
        market=market,
        remote_mode="remote",
        employment_type="full-time",
        location_country="Remote",
        location_region=None,
        location_city=None,
        compensation_min=comp_min,
        compensation_max=None,
        compensation_currency="USD",
        canonical_posted_at=rec.discovered_at or datetime.utcnow(),
        first_seen_at=rec.fetched_at,
        last_seen_at=rec.fetched_at,
        active_posting_count=1,
        source_count=1,
        ghost_score=None,
        canonical_status="active",
        merge_confidence=0.75,
        merge_reasons=[f"{source}-direct"],
    )


def fetch_all_wave1(limit_per_source: int = 8) -> list[CanonicalJob]:
    """Fetch with robust handling (Phase 0+)."""
    jobs: list[CanonicalJob] = []

    connectors = [
        ("remoteok", lambda: RemoteOKConnector().fetch(limit=limit_per_source).records),
        ("weworkremotely", lambda: WeWorkRemotelyConnector().fetch(limit=limit_per_source).records),
        ("arcdev", lambda: ArcDevConnector().fetch(limit=limit_per_source).records),
        ("wellfound", lambda: WellfoundConnector().fetch(limit=limit_per_source).records),
        ("workable", lambda: WorkableConnector(subdomain="epignosis").fetch(limit=3).records),
    ]

    for name, fetcher in connectors:
        try:
            for rec in fetcher():
                cj = _to_canonical(rec, name)
                if cj:
                    jobs.append(cj)
        except Exception as e:
            logger.warning(f"Source {name} failed: {e}")

    for ch in ["tonhunt", "cryptohiring_1"]:
        try:
            for rec in TelegramConnector.from_channel(ch).fetch(limit=4).records:
                cj = _to_canonical(rec, f"telegram:{ch}")
                if cj:
                    jobs.append(cj)
        except Exception as e:
            logger.warning(f"Telegram {ch} failed: {e}")

    seen = set()
    deduped: list[CanonicalJob] = []
    for j in jobs:
        key = (j.title_normalized[:60] if j.title_normalized else "", (j.company_name or "").lower()[:40])
        if key not in seen:
            seen.add(key)
            deduped.append(j)
    return deduped


def run_full_pipeline(limit_per_source: int = 8) -> dict:
    """Run with metrics (Phase 0 success)."""
    profile = get_alina_profile()
    canonical_jobs = fetch_all_wave1(limit_per_source)

    raw_count = len(canonical_jobs)
    sources = sorted({j.canonical_job_id.split("-")[0].split(":")[0] for j in canonical_jobs})

    if not canonical_jobs:
        logger.warning("No jobs fetched")
        return {
            "profile": profile,
            "ranked_jobs": [],
            "digest": {},
            "total_raw": 0,
            "sources": [],
            "metrics": {"raw_count": 0, "ranked_count": 0},
        }

    ranked = rank_jobs(profile, canonical_jobs)
    apply_ghost_penalty(ranked)

    digest = build_digest(profile, ranked, limit=12)

    ranked_count = len(ranked)
    metrics = {
        "raw_count": raw_count,
        "ranked_count": ranked_count,
        "sources_used": len(sources),
    }

    if raw_count < 5:
        logger.warning("Low volume in this run")

    logger.info(f"Pipeline: raw={raw_count}, ranked={ranked_count}")

    return {
        "profile": profile,
        "ranked_jobs": ranked,
        "digest": digest,
        "total_raw": raw_count,
        "sources": sources,
        "metrics": metrics,
    }
