"""
Segment Scorer for Web3 Ops / DAO / Governance / Treasury / Contributor roles.

Central place for positive boosters, negative filters, and weighted scoring.
Used by quality evals and (later) main pipeline.
"""

import re
from typing import Dict, List, Tuple

# === POSITIVE BOOSTERS (high weight for target segment) ===
STRONG_SENIORITY = [
    "head of operations", "head of ops", "senior operations manager",
    "senior ops", "operations lead", "lead operations", "governance lead",
    "treasury manager", "dao ops", "contributor operations", "on-chain operations",
    "program manager dao", "chief of staff"
]

STRONG_DOMAIN = [
    "dao", "governance", "treasury", "contributor", "on-chain",
    "program manager", "dao ops", "snapshot", "multisig", "proposal"
]

CRYPTO_NATIVE_BONUS = [
    "gnosis safe", "snapshot", "multisig", "proposal", "on-chain",
    "governance", "dao", "treasury", "contributor"
]

# === NEGATIVE PATTERNS (strong filters) ===
NEGATIVE_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(?:associate|junior|jr\.|entry level|coordinator|specialist|analyst)\b", re.I),
    re.compile(r"\b(?:revenue operations|sales operations|marketing operations|finance operations)\b", re.I),
    re.compile(r"\b(?:trading operations?|clearing|risk operations|compliance operations)\b", re.I),
    re.compile(r"\b(?:customer success|customer operations|client operations)\b", re.I),
    re.compile(r"\b(?:it operations|design operations|property operations|facilities)\b", re.I),
    # Centralized exchange / regulatory licensing roles (off-segment for DAO Ops / Governance / Treasury)
    re.compile(r"\b(?:centralized exchange|cex|licensing|regulatory program|broker-dealer|msb|dcm|ats)\b", re.I),
    re.compile(r"\b(?:fcm|dco|surveillance vendor|kyc provider|exchange licensing)\b", re.I),
    re.compile(r"\b(?:night shift|shift work)\b", re.I),
    re.compile(r"\b(?:developer|engineer|solidity|smart contract|frontend|backend)\b", re.I),
]

def load_thresholds(config_path: str = "config/source_config.yaml") -> Dict[str, float]:
    """Load per-source accepted_relevance_threshold from config."""
    import yaml
    try:
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}
        thresholds = {}
        for src, data in cfg.get("thresholds", {}).items():
            if isinstance(data, dict) and "accepted_relevance_threshold" in data:
                thresholds[src.lower()] = float(data["accepted_relevance_threshold"])
        return thresholds
    except Exception:
        # Safe defaults matching current config
        return {
            "web3career": 0.20,
            "remote3": 0.20,
            "findweb3": 0.35,
            "protocol_seeds": 0.40,
            "cryptojobslist": 0.25,
        }

def compute_segment_score(title: str, description: str = "", source: str = "") -> Dict:
    """
    Returns structured score with explainable components.
    """
    text = f"{title} {description}".lower()
    reasons = []
    score = 0.0

    # Base segment signal
    has_ops = any(k in text for k in ["ops", "operation", "operations"])
    if has_ops:
        score += 0.15
        reasons.append("has_ops")

    # Strong seniority (high weight)
    has_strong_seniority = any(kw in text for kw in STRONG_SENIORITY)
    if has_strong_seniority:
        score += 0.40
        reasons.append("strong_seniority")

    # Strong domain
    has_strong_domain = any(kw in text for kw in STRONG_DOMAIN)
    if has_strong_domain:
        score += 0.35
        reasons.append("strong_domain")

    # Crypto-native bonus
    crypto_bonus = sum(1 for term in CRYPTO_NATIVE_BONUS if term in text)
    if crypto_bonus > 0:
        bonus = min(0.15, 0.05 * crypto_bonus)
        score += bonus
        reasons.append(f"crypto_native_bonus(+{bonus:.2f})")

    # Remote / async bonus (light)
    if any(x in text for x in ["remote", "async", "distributed"]):
        score += 0.05
        reasons.append("remote_bonus")

    # Negative penalties
    for pat in NEGATIVE_PATTERNS:
        if pat.search(text):
            score -= 0.25
            reasons.append(f"negative:{pat.pattern[:30]}")
            break  # one strong negative is enough

    # Strict combo bonus
    if has_strong_seniority and has_strong_domain:
        score += 0.10
        reasons.append("seniority+domain_combo")

    final_score = max(0.0, min(1.0, round(score, 3)))

    return {
        "score": final_score,
        "has_strong_seniority": has_strong_seniority,
        "has_strong_domain": has_strong_domain,
        "crypto_native_bonus": crypto_bonus > 0,
        "reasons": reasons,
        "passes_strict": has_strong_seniority and has_strong_domain,
    }

def passes_source_threshold(score: float, source: str, thresholds: Dict[str, float] = None) -> bool:
    """Check if score meets the source-specific threshold."""
    if thresholds is None:
        thresholds = load_thresholds()
    threshold = thresholds.get(source.lower(), 0.25)
    return score >= threshold

def score_and_filter(item: Dict, source: str) -> Dict:
    """Convenience: score + decide high_relevance using source threshold."""
    title = item.get("title", "")
    desc = item.get("description", "") or ""
    scoring = compute_segment_score(title, desc, source)

    thresholds = load_thresholds()
    meets_threshold = passes_source_threshold(scoring["score"], source, thresholds)

    return {
        **scoring,
        "meets_source_threshold": meets_threshold,
        "threshold_used": thresholds.get(source.lower(), 0.25),
        "high_relevance_for_source": scoring["passes_strict"] and meets_threshold,
    }
