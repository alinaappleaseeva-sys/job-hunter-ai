"""Ranking v1: explainable heuristic scoring for a CandidateProfile against CanonicalJobs.

Principles:
- Heuristics before any ML.
- Every score component produces human-readable reasons.
- Short, reviewable, tunable via weights only after eval.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from job_hunter_ai.normalization.fields.requirements import extract_hard_requirements
from job_hunter_ai.common.models import (
    CandidateProfile,
    CanonicalJob,
    JobScoreBreakdown,
    RankedJob,
    ScoreExplanation,
)

logger = logging.getLogger(__name__)

CONFIG_PATH = Path("config/ranking_weights.json")

def load_weights() -> dict[str, float]:
    """Load weights from config or fall back to defaults (Phase 2).
    Adds validation: warn if sum != ~1.0 or file missing.
    """
    defaults = {
        "role_fit": 0.35,
        "seniority_fit": 0.22,
        "location_remote_fit": 0.18,
        "salary_fit": 0.05,
        "market_fit": 0.08,
        "recency_fit": 0.12,
    }
    if not CONFIG_PATH.exists():
        logger.warning(f"Ranking weights config {CONFIG_PATH} not found, using defaults")
        return defaults
    try:
        with open(CONFIG_PATH) as f:
            loaded = json.load(f)
        for k in defaults:
            if k in loaded and isinstance(loaded[k], (int, float)):
                defaults[k] = float(loaded[k])
        total = sum(defaults.values())
        if abs(total - 1.0) > 0.02:
            logger.warning(f"Ranking weights sum to {total:.3f} (expected ~1.0)")
        logger.info(f"Loaded ranking weights from {CONFIG_PATH}: {defaults}")
    except Exception as e:
        logger.warning(f"Failed to load weights from config: {e}, using defaults")
    return defaults

DEFAULT_WEIGHTS = load_weights()


def _normalize(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(text.lower().split())


def _contains_any(text: str, keywords: list[str]) -> bool:
    t = _normalize(text)
    return any(kw in t for kw in (k.lower() for k in keywords if k))


def _score_role_fit(profile: CandidateProfile, job: CanonicalJob) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0

    title = job.title_normalized or ""
    role_family = job.role_family or ""

    kw_match = _contains_any(title, profile.target_title_keywords)
    family_match = role_family in profile.target_role_families if profile.target_role_families else False

    # Phase 2: High-priority title boosts for CoS / Head of Ops (capped at 1.0)
    high_priority = ["chief of staff", "head of operations", "head of ops", "dao", "governance", "treasury ops"]
    priority_boost = 0.0
    for hp in high_priority:
        if hp in title:
            priority_boost = 0.15
            reasons.append(f"high-priority title boost: {hp}")
            break

    if kw_match and family_match:
        score = 1.0
        reasons.append(f"title matches keywords {profile.target_title_keywords} and role_family={role_family}")
    elif kw_match or family_match:
        score = 0.7
        reasons.append("partial role match (keywords or family)")
    else:
        score = 0.2
        reasons.append("weak role signal")

    score = min(1.0, score + priority_boost)
    return score, reasons


def _score_seniority_fit(profile: CandidateProfile, job: CanonicalJob) -> tuple[float, list[str]]:
    reasons: list[str] = []
    job_sen = (job.seniority or "").lower()
    targets = [s.lower() for s in profile.target_seniorities]

    if not job_sen:
        return 0.5, ["seniority unknown in job"]

    if job_sen in targets:
        return 1.0, [f"seniority {job_sen} exactly in target list"]

    # Simple band proximity
    order = ["junior", "mid", "senior", "lead", "staff", "head"]
    try:
        j_idx = order.index(job_sen)
        best = min((abs(j_idx - order.index(t)) for t in targets if t in order), default=2)
        score = max(0.3, 1.0 - 0.35 * best)
        reasons.append(f"seniority {job_sen} close to targets (band distance {best})")
        return score, reasons
    except ValueError:
        return 0.4, [f"seniority {job_sen} not in known bands"]

    return 0.5, ["no strong seniority signal"]


def _score_location_remote_fit(profile: CandidateProfile, job: CanonicalJob) -> tuple[float, list[str]]:
    reasons: list[str] = []
    pref = (profile.remote_preference or "any").lower()
    job_remote = (job.remote_mode or "unknown").lower()
    job_loc = job.location_country or ""

    if pref in ("any", None):
        score = 0.95
        reasons.append("profile accepts any location/remote")
        return score, reasons

    if pref == "remote":
        if job_remote == "remote":
            score = 1.0
            reasons.append("exact remote match")
        elif job_remote in ("hybrid", "unknown"):
            score = 0.6
            reasons.append("hybrid/unknown when remote preferred")
        else:
            score = 0.2
            reasons.append("onsite conflicts remote preference")
    elif pref == job_remote:
        score = 0.9
        reasons.append(f"remote mode {job_remote} matches preference")
    else:
        score = 0.5
        reasons.append("location/remote partial match")

    if profile.preferred_locations and any(loc.lower() in (job_loc or "").lower() for loc in profile.preferred_locations):
        score = min(1.0, score + 0.1)
        reasons.append("preferred location/country present")

    return score, reasons


def _score_salary_fit(profile: CandidateProfile, job: CanonicalJob) -> tuple[float, list[str]]:
    reasons: list[str] = []
    if not profile.min_compensation:
        return 0.8, ["no min compensation specified in profile"]

    job_min = job.compensation_min
    if job_min is None:
        return 0.7, ["salary not disclosed in job"]

    if job_min >= profile.min_compensation:
        score = 1.0
        reasons.append(f"job min {job_min} meets or exceeds profile min {profile.min_compensation}")
    else:
        gap = (profile.min_compensation - job_min) / max(profile.min_compensation, 1)
        score = max(0.3, 1.0 - gap * 0.7)
        reasons.append(f"job compensation below target (gap factor {gap:.2f})")

    return score, reasons


def _score_market_fit(profile: CandidateProfile, job: CanonicalJob) -> tuple[float, list[str]]:
    reasons: list[str] = []
    job_market = (job.market or "").lower()
    targets = [m.lower() for m in profile.preferred_markets]

    if not targets:
        return 0.85, ["no market preference specified"]

    if job_market and job_market in targets:
        return 1.0, [f"market {job_market} in preferred list"]

    if job_market:
        return 0.5, [f"market {job_market} not in preferred markets"]
    return 0.6, ["market unknown"]

from datetime import UTC, datetime

def _days_since(dt: datetime | None) -> float:
    if dt is None:
        return 999.0
    now = datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    delta = now - dt
    return max(0.0, delta.days + delta.seconds / 86400)


def _score_recency_fit(job: CanonicalJob) -> tuple[float, list[str]]:
    """Separate recency component.
    Strong downrank for 21-40 days, hard preference for fresh jobs.
    Jobs >40 days should be filtered upstream.
    """
    reasons = []
    age = _days_since(job.canonical_posted_at)

    if age > 40:
        score = 0.0
        reasons.append(f"older than 40 days (age≈{age:.0f}d) — hard filtered upstream")
    elif age <= 7:
        score = 1.0
        reasons.append(f"very fresh (≤7 days, age≈{age:.0f}d)")
    elif age <= 14:
        score = 0.85
        reasons.append(f"fresh (8-14 days, age≈{age:.0f}d)")
    elif age <= 21:
        score = 0.65
        reasons.append(f"recent (15-21 days, age≈{age:.0f}d)")
    elif age <= 30:
        score = 0.40
        reasons.append(f"aging (22-30 days, age≈{age:.0f}d) — strong downrank")
    else:  # 31-40
        score = 0.20
        reasons.append(f"stale (31-40 days, age≈{age:.0f}d) — heavy penalty")

    return round(score, 3), reasons


def _score_requirements_mismatch(profile: CandidateProfile, job: CanonicalJob) -> tuple[float, list[str]]:
    """Basic hard credential mismatch penalty.

    Looks for obvious accounting/CPA/SOX requirements in available description text.
    Returns low score + explanation when mismatch is detected for our profile.
    """
    reasons = []
    # Try to find raw description in common places
    desc = ""
    if hasattr(job, "description") and job.description:
        desc = job.description
    if not desc and hasattr(job, "payload") and isinstance(getattr(job, "payload", None), dict):
        desc = job.payload.get("description", "") or ""
    if not desc and hasattr(job, "raw_description"):
        desc = getattr(job, "raw_description", "") or ""

    req = extract_hard_requirements(desc)
    if req.get("requires_accounting_credential"):
        reasons.append("hard credential mismatch (CPA/Big 4/SOX/GAAP/public accounting required)")
        return 0.15, reasons   # strong penalty

    if req.get("raw_signals"):
        reasons.append("some credential signals present but not blocking")
        return 0.7, reasons

    return 0.95, ["no strong credential mismatch detected"]


def compute_score_breakdown(
    profile: CandidateProfile, job: CanonicalJob, weights: dict[str, float] | None = None
) -> JobScoreBreakdown:
    weights = weights or DEFAULT_WEIGHTS

    role_s, role_r = _score_role_fit(profile, job)
    sen_s, sen_r = _score_seniority_fit(profile, job)
    loc_s, loc_r = _score_location_remote_fit(profile, job)
    sal_s, sal_r = _score_salary_fit(profile, job)
    mkt_s, mkt_r = _score_market_fit(profile, job)
    rec_s, rec_r = _score_recency_fit(job)
    req_s, req_r = _score_requirements_mismatch(profile, job)   # from PR

    rec_w = weights.get("recency_fit", 0.0)
    req_weight = 0.10   # modest weight for requirements mismatch penalty

    total = (
        role_s * weights["role_fit"]
        + sen_s * weights["seniority_fit"]
        + loc_s * weights["location_remote_fit"]
        + sal_s * weights["salary_fit"]
        + mkt_s * weights["market_fit"]
        + rec_s * rec_w
        + req_s * req_weight
    )

    explanations: list[ScoreExplanation] = [
        ScoreExplanation(component="role_fit", score=role_s, reasons=role_r),
        ScoreExplanation(component="seniority_fit", score=sen_s, reasons=sen_r),
        ScoreExplanation(component="location_remote_fit", score=loc_s, reasons=loc_r),
        ScoreExplanation(component="salary_fit", score=sal_s, reasons=sal_r),
        ScoreExplanation(component="market_fit", score=mkt_s, reasons=mkt_r),
        ScoreExplanation(component="recency_fit", score=rec_s, reasons=rec_r),
        ScoreExplanation(component="requirements_mismatch", score=req_s, reasons=req_r),
    ]

    return JobScoreBreakdown(
        role_fit=role_s,
        seniority_fit=sen_s,
        location_remote_fit=loc_s,
        salary_fit=sal_s,
        market_fit=mkt_s,
        recency_fit=rec_s,
        requirements_mismatch=req_s,
        total_score=round(total, 3),
        explanations=explanations,
    )

def rank_jobs(
    profile: CandidateProfile,
    jobs: Sequence[CanonicalJob],
    weights: dict[str, float] | None = None,
) -> list[RankedJob]:
    """Rank canonical jobs for the given candidate profile.

    Returns list sorted by total_score desc, with rank and explanations populated.
    Phase 2: always log top breakdowns for observability.
    """
    if not jobs:
        return []

    weights = weights or DEFAULT_WEIGHTS
    ranked: list[RankedJob] = []
    for job in jobs:
        breakdown = compute_score_breakdown(profile, job, weights)
        ranked.append(RankedJob(canonical_job=job, score_breakdown=breakdown))

    ranked.sort(key=lambda r: r.score_breakdown.total_score, reverse=True)

    for i, rj in enumerate(ranked, 1):
        rj.rank = i
        if i <= 5:
            logger.info(f"Top {i}: {rj.canonical_job.title_normalized}@{rj.canonical_job.company_name} "
                         f"score={rj.score_breakdown.total_score:.3f} role_fit={rj.score_breakdown.role_fit:.2f} "
                         f"market={rj.canonical_job.market}")

    logger.info(f"rank_jobs: {len(ranked)} jobs, weights={weights}")
    return ranked


def simple_chrono_baseline(jobs: Sequence[CanonicalJob]) -> list[CanonicalJob]:
    """Naive baseline: sort by posted_at desc (for eval comparison)."""
    return sorted(
        jobs,
        key=lambda j: j.canonical_posted_at or datetime.min,
        reverse=True,
    )
