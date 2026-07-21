"""Core pipeline for job aggregation and ranking (Phase 0-3 foundations + robust expansion).

Includes:
- get_alina_profile()
- fetch_all_wave1() with robust ATS (Greenhouse/Lever/Ashby) + Telegram
- Config-driven source lists (config/source_config.yaml)
- Parallel fetch + backoff + error recovery
- Strengthened dedup (fuzzy title+company)
- Metrics: raw/ranked per source, target_role_family_count, volume delta
"""

from __future__ import annotations

import logging
import re
import time
import functools
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from job_hunter_ai.common.models import CanonicalJob, CandidateProfile
from job_hunter_ai.profiles.alina import get_alina_profile
from job_hunter_ai.connectors.arcdev import ArcDevConnector
from job_hunter_ai.connectors.ashby import AshbyConnector
from job_hunter_ai.connectors.greenhouse import GreenhouseConnector
from job_hunter_ai.connectors.lever import LeverConnector
from job_hunter_ai.connectors.remoteok import RemoteOKConnector
from job_hunter_ai.connectors.telegram import TelegramConnector
from job_hunter_ai.connectors.weworkremotely import WeWorkRemotelyConnector
from job_hunter_ai.connectors.wellfound import WellfoundConnector
from job_hunter_ai.connectors.workable import WorkableConnector
from job_hunter_ai.delivery import build_digest
from job_hunter_ai.ghosting.ghosting import apply_ghost_penalty
from job_hunter_ai.ranking.ranking import rank_jobs

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "ats": {"greenhouse": {"boards": ["aave", "optimism"]}, "lever": {"sites": []}, "ashby": {"boards": []}},
    "telegram": {"channels": ["cryptohiring_1", "tonhunt"]},
    "robustness": {"max_retries": 2, "backoff_base_seconds": 1.5, "concurrency": 4},
}

CONFIG_PATH = Path("config/source_config.yaml")


def _load_source_config() -> dict:
    if not CONFIG_PATH.exists():
        logger.warning(f"{CONFIG_PATH} not found, using minimal defaults")
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f) or {}


def _to_canonical(rec: Any, source: str) -> CanonicalJob | None:
    """Phase 2 detection + Phase 3 robustness."""
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
    desc = str(payload.get("description") or payload.get("content") or "").lower()
    tags = [t.lower() for t in (payload.get("tags") or [])]
    full_text = f"{title_lower} {desc} {' '.join(tags)}"

    market = "web3"
    if any(k in full_text for k in ["security", "cyber", "infosec"]):
        market = "security"
    elif any(k in full_text for k in ["ai", "llm", "agent", "ml"]):
        market = "ai-web3"
    elif not any(k in full_text for k in ["web3", "crypto", "defi", "dao", "blockchain", "fintech"]):
        market = "saas"

    role_family = "other"
    if any(k in full_text for k in ["chief of staff", "head of operations", "head of ops"]):
        role_family = "chief_of_staff"
    elif any(k in full_text for k in ["governance", "treasury", "dao ops", "program management", "program manager"]):
        role_family = "dao_ops"
    elif any(k in full_text for k in ["ops", "operations", "program", "head of"]):
        role_family = "operations"

    seniority = "senior" if any(k in title_lower for k in ["senior", "lead", "head", "manager", "chief"]) else "mid"

    comp_min = None
    salary = str(payload.get("salary") or payload.get("compensation") or payload.get("salary_range") or "")
    salary_lower = salary.lower()
    for num in ["160", "150", "180", "170", "140", "130", "120", "110"]:
        if num in salary_lower:
            comp_min = int(num) * 1000
            break
    if comp_min is None:
        m = re.search(r'\$?\s*(\d{2,3})\s*[kK]', desc)
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


def _fetch_with_retry(fetcher, name: str, max_retries: int = 2, backoff: float = 1.5):
    """Simple exponential backoff + error recovery."""
    for attempt in range(max_retries + 1):
        try:
            return fetcher()
        except Exception as e:
            if attempt == max_retries:
                logger.exception(f"{name} failed after {max_retries} retries")
                return []
            sleep = backoff * (2 ** attempt)
            logger.info(f"{name} transient error (attempt {attempt+1}), sleeping {sleep:.1f}s")
            time.sleep(sleep)
    return []


def fetch_ats_wave(config: dict, limit_per: int = 15) -> list[CanonicalJob]:
    """Phase 3: robust parallel fetch from Greenhouse/Lever/Ashby using config."""
    jobs: list[CanonicalJob] = []
    robustness = config.get("robustness", {})
    max_retries = robustness.get("max_retries", 2)
    backoff = robustness.get("backoff_base_seconds", 1.5)
    concurrency = robustness.get("concurrency", 4)

    ats = config.get("ats", {})
    tasks = []

    # Greenhouse
    for board in ats.get("greenhouse", {}).get("boards", []):
        def _fetch_green(b):
            return [
                _to_canonical(rec, f"greenhouse:{b}")
                for rec in GreenhouseConnector(b).fetch(limit=limit_per).records
            ]
        tasks.append((f"greenhouse:{board}", functools.partial(_fetch_green, board)))

    # Lever
    for site in ats.get("lever", {}).get("sites", []):
        def _fetch_lever(s):
            return [
                _to_canonical(rec, f"lever:{s}")
                for rec in LeverConnector(s).fetch(limit=limit_per).records
            ]
        tasks.append((f"lever:{site}", functools.partial(_fetch_lever, site)))

    # Ashby
    for board in ats.get("ashby", {}).get("boards", []):
        def _fetch_ashby(b):
            return [
                _to_canonical(rec, f"ashby:{b}")
                for rec in AshbyConnector(b).fetch(limit=limit_per).records
            ]
        tasks.append((f"ashby:{board}", functools.partial(_fetch_ashby, board)))

    if not tasks:
        return jobs

    with ThreadPoolExecutor(max_workers=min(concurrency, len(tasks))) as executor:
        future_to_name = {executor.submit(lambda f=f: _fetch_with_retry(f, name, max_retries, backoff)): name
                          for name, f in tasks}
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                recs = future.result()
                for cj in recs:
                    if cj:
                        jobs.append(cj)
            except Exception as e:
                logger.exception(f"ATS task {name} failed")

    return jobs


def fetch_all_wave1(limit_per_source: int = 8) -> list[CanonicalJob]:
    """Phase 3 robust version."""
    config = _load_source_config()
    jobs: list[CanonicalJob] = []

    # Core boards (always)
    core = [
        ("remoteok", lambda: RemoteOKConnector().fetch(limit=limit_per_source).records),
        ("weworkremotely", lambda: WeWorkRemotelyConnector().fetch(limit=limit_per_source).records),
        ("arcdev", lambda: ArcDevConnector().fetch(limit=limit_per_source).records),
        ("wellfound", lambda: WellfoundConnector().fetch(limit=limit_per_source).records),
    ]

    robustness = config.get("robustness", {})
    max_retries = robustness.get("max_retries", 2)
    backoff = robustness.get("backoff_base_seconds", 1.5)

    for name, fetcher in core:
        recs = _fetch_with_retry(fetcher, name, max_retries, backoff)
        for rec in recs:
            cj = _to_canonical(rec, name)
            if cj:
                jobs.append(cj)

    # ATS wave (Phase 3)
    ats_jobs = fetch_ats_wave(config, limit_per=limit_per_source)
    jobs.extend(ats_jobs)

    # Telegram (expanded from config)
    tg_channels = config.get("telegram", {}).get("channels", ["cryptohiring_1", "tonhunt"])
    for ch in tg_channels:
        try:
            for rec in TelegramConnector.from_channel(ch).fetch(limit=5).records:
                cj = _to_canonical(rec, f"telegram:{ch}")
                if cj:
                    jobs.append(cj)
        except Exception as e:
            logger.warning(f"Telegram {ch} failed: {e}")

    # Strengthened dedup (Phase 3): canonical_job_id + fuzzy title+company
    seen = set()
    deduped: list[CanonicalJob] = []
    for j in jobs:
        # prefer canonical id if present, else fuzzy
        key = (j.canonical_job_id or "", (j.title_normalized or "")[:50], (j.company_name or "").lower()[:30])
        if key not in seen:
            seen.add(key)
            deduped.append(j)

    return deduped



def _apply_recency_filter(jobs: list[CanonicalJob], max_age_days: int = 40) -> tuple[list[CanonicalJob], int]:
    """Hard drop jobs older than max_age_days before ranking.
    Returns (filtered_jobs, dropped_count)
    """
    from datetime import datetime, UTC

    def _days_since(dt):
        if dt is None:
            return 999.0
        now = datetime.now(UTC)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        delta = now - dt
        return max(0.0, delta.days + delta.seconds / 86400)

    kept = []
    dropped = 0
    for j in jobs:
        age = _days_since(getattr(j, "canonical_posted_at", None))
        if age <= max_age_days:
            kept.append(j)
        else:
            dropped += 1
    return kept, dropped


def run_full_pipeline(limit_per_source: int = 8) -> dict:
    """Run with Phase 3 metrics (volume delta, target roles)."""
    profile = get_alina_profile()
    cfg = _load_source_config()
    canonical_jobs = fetch_all_wave1(limit_per_source)
    raw_count = len(canonical_jobs)

    # Hard recency filter (>40 days by default)
    recency_cfg = cfg.get("recency", {})
    max_age = recency_cfg.get("hard_max_age_days", 40)
    canonical_jobs, dropped_old = _apply_recency_filter(canonical_jobs, max_age)

    sources = sorted({j.canonical_job_id.split("-")[0].split(":")[0] for j in canonical_jobs}) if canonical_jobs else []

    if not canonical_jobs:
        logger.warning(f"No jobs after recency filter (dropped {dropped_old} old jobs)")
        return {
            "profile": profile,
            "ranked_jobs": [],
            "digest": {},
            "total_raw": raw_count,
            "sources": [],
            "metrics": {"raw_count": raw_count, "ranked_count": 0, "recency_dropped": dropped_old},
        }

    if dropped_old > 0:
        logger.info(f"Recency filter: dropped {dropped_old} jobs older than {max_age} days")

    ranked = rank_jobs(profile, canonical_jobs)
    apply_ghost_penalty(ranked)

    digest = build_digest(profile, ranked, limit=12)

    ranked_count = len(ranked)
    target_roles = sum(1 for j in canonical_jobs if j.role_family in profile.target_role_families)
    metrics = {
        "raw_count": raw_count,
        "ranked_count": ranked_count,
        "recency_dropped": dropped_old,
        "sources_used": len(sources),
        "target_role_family_count": target_roles,
        "target_role_ratio": round(target_roles / max(raw_count, 1), 3),
    }

    if raw_count < 5:
        logger.warning("Low volume in this run")

    logger.info(f"Pipeline: raw={raw_count}, ranked={ranked_count}, target_roles={target_roles}")

    return {
        "profile": profile,
        "ranked_jobs": ranked,
        "digest": digest,
        "total_raw": raw_count,
        "sources": sources,
        "metrics": metrics,
    }
