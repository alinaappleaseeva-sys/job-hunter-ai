"""Ranking v1: explainable heuristic scoring for a CandidateProfile against CanonicalJobs.

Principles:
- Heuristics before any ML.
- Every score component produces human-readable reasons.
- Short, reviewable, tunable via weights only after eval.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from job_hunter_ai.common.models import (
    CandidateProfile,
    CanonicalJob,
    JobScoreBreakdown,
    RankedJob,
    ScoreExplanation,
)

logger = logging.getLogger(__name__)

# Default weights (sum to 1.0)
DEFAULT_WEIGHTS = {
    "role_fit": 0.30,
    "seniority_fit": 0.25,
    "location_remote_fit": 0.20,
    "salary_fit": 0.15,
    "market_fit": 0.10,
}


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

    if kw_match and family_match:
        score = 1.0
        reasons.append(f"title matches keywords {profile.target_title_keywords} and role_family={role_family}")
    elif kw_match or family_match:
        score = 0.7
        reasons.append("partial role match (keywords or family)")
    else:
        score = 0.2
        reasons.append("weak role signal")

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


def compute_score_breakdown(
    profile: CandidateProfile, job: CanonicalJob, weights: dict[str, float] | None = None
) -> JobScoreBreakdown:
    weights = weights or DEFAULT_WEIGHTS

    role_s, role_r = _score_role_fit(profile, job)
    sen_s, sen_r = _score_seniority_fit(profile, job)
    loc_s, loc_r = _score_location_remote_fit(profile, job)
    sal_s, sal_r = _score_salary_fit(profile, job)
    mkt_s, mkt_r = _score_market_fit(profile, job)

    total = (
        role_s * weights["role_fit"]
        + sen_s * weights["seniority_fit"]
        + loc_s * weights["location_remote_fit"]
        + sal_s * weights["salary_fit"]
        + mkt_s * weights["market_fit"]
    )

    explanations: list[ScoreExplanation] = [
        ScoreExplanation(component="role_fit", score=role_s, reasons=role_r),
        ScoreExplanation(component="seniority_fit", score=sen_s, reasons=sen_r),
        ScoreExplanation(component="location_remote_fit", score=loc_s, reasons=loc_r),
        ScoreExplanation(component="salary_fit", score=sal_s, reasons=sal_r),
        ScoreExplanation(component="market_fit", score=mkt_s, reasons=mkt_r),
    ]

    return JobScoreBreakdown(
        role_fit=role_s,
        seniority_fit=sen_s,
        location_remote_fit=loc_s,
        salary_fit=sal_s,
        market_fit=mkt_s,
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
    """
    if not jobs:
        return []

    ranked: list[RankedJob] = []
    for job in jobs:
        breakdown = compute_score_breakdown(profile, job, weights)
        ranked.append(RankedJob(canonical_job=job, score_breakdown=breakdown))

    ranked.sort(key=lambda r: r.score_breakdown.total_score, reverse=True)

    for i, rj in enumerate(ranked, 1):
        rj.rank = i

    return ranked


def simple_chrono_baseline(jobs: Sequence[CanonicalJob]) -> list[CanonicalJob]:
    """Naive baseline: sort by posted_at desc (for eval comparison)."""
    return sorted(
        jobs,
        key=lambda j: j.canonical_posted_at or datetime.min,
        reverse=True,
    )
