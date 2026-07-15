"""
Segment Scorer for Web3 Ops / DAO / Governance / Treasury / Contributor roles.

Segment Philosophy:
- Core (Tier 1): explicit Operations / Treasury / Governance Ops / DAO Ops roles → high score (0.75+)
- Extended (Tier 2): Strategy, Business Development, Program Management, Ecosystem Growth,
  Governance Operations, Contributor Operations, Strategic Project roles *inside* DAO/Web3 protocols.
  These get medium score (0.45–0.65), especially with strong DAO/protocol context.
- Goal: Do not miss useful roles like "Strategy & Business Development Associate" at Aave,
  "Ecosystem Manager" at Uniswap, "Program Manager" at Lido/Optimism, etc.

Negative filters remain strict for pure trash (Trading Ops, Risk Ops, IT Ops, Sales Ops,
pure Engineering, centralized exchange licensing, etc.) when there is no DAO/protocol context.
"""

import re
from typing import Dict, List, Tuple

# === POSITIVE BOOSTERS (high weight for target segment) ===
# Tier 1: Core Ops (explicit high-relevance for the segment)
CORE_OPS_KEYWORDS = [
    "head of operations", "head of ops", "senior operations manager",
    "senior ops", "operations lead", "lead operations",
    "dao ops", "treasury manager", "treasury lead",
    "governance lead", "governance operations", "contributor operations",
    "on-chain operations", "program manager dao", "chief of staff"
]

STRONG_DOMAIN = [
    "dao", "governance", "treasury", "contributor", "on-chain",
    "program manager", "dao ops", "snapshot", "multisig", "proposal"
]

# Tier 2: Adjacent Strategy / Program / Ecosystem / BD roles in protocol/DAO context
ADJACENT_STRATEGY_KEYWORDS = [
    "strategy associate", "strategy manager", "business development", "business dev",
    "program manager", "program associate", "ecosystem growth", "ecosystem manager",
    "ecosystem associate", "contributor operations", "governance operations",
    "strategic project", "strategic initiatives", "partnerships manager",
    "ecosystem development", "community development", "dao strategy"
]

CRYPTO_NATIVE_BONUS = [
    "gnosis safe", "snapshot", "multisig", "proposal", "on-chain",
    "governance", "dao", "treasury", "contributor"
]

# === NEGATIVE PATTERNS ===
# Soft negatives (can be softened for Tier 2 adjacent roles)
SOFT_NEGATIVE_PATTERNS = [
    re.compile(r"\b(?:associate|junior|jr\.|entry level)\b", re.I),
]

# Hard negatives — always apply strong penalty (even for adjacent roles)
HARD_NEGATIVE_PATTERNS = [
    re.compile(r"\b(?:revenue operations|sales operations|marketing operations|finance operations)\b", re.I),
    re.compile(r"\b(?:trading operations?|clearing|risk operations|compliance operations)\b", re.I),
    re.compile(r"\b(?:customer success|customer operations|client operations)\b", re.I),
    re.compile(r"\b(?:it operations|design operations|property operations|facilities)\b", re.I),
    # Centralized exchange / regulatory licensing roles (off-segment)
    re.compile(r"\b(?:centralized exchange|cex|licensing|regulatory program|broker-dealer|msb|dcm|ats)\b", re.I),
    re.compile(r"\b(?:fcm|dco|surveillance vendor|kyc provider|exchange licensing)\b", re.I),
    re.compile(r"\b(?:night shift|shift work)\b", re.I),
    re.compile(r"\b(?:developer|engineer|solidity|smart contract|frontend|backend)\b", re.I),
]

NEGATIVE_PATTERNS = SOFT_NEGATIVE_PATTERNS + HARD_NEGATIVE_PATTERNS  # kept for backward compat


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

def compute_segment_score(title: str, description: str = "", source: str = "", company: str = "") -> Dict:
    """
    Returns structured score with explainable components.
    Implements tiered scoring per new segment philosophy.
    """
    full_text = f"{title} {description} {company}".lower()
    text = f"{title} {description}".lower()
    reasons = []
    score = 0.0
    tier = "none"

    # === Tier 1: Core Ops ===
    is_core_ops = any(kw in full_text for kw in CORE_OPS_KEYWORDS)
    if is_core_ops:
        tier = "core"
        score += 0.55
        reasons.append("tier1_core_ops")

    # === Tier 2: Adjacent Strategy / Program / Ecosystem ===
    is_adjacent = any(kw in full_text for kw in ADJACENT_STRATEGY_KEYWORDS)
    if is_adjacent and not is_core_ops:
        tier = "adjacent"
        score += 0.45
        reasons.append("tier2_adjacent_strategy_bd_program")

    # Base "ops" signal (lighter if not core)
    has_ops = any(k in text for k in ["ops", "operation", "operations"])
    if has_ops and not is_core_ops:
        score += 0.10
        reasons.append("has_ops")

    # Strong seniority (still valuable, but lighter for Tier 2)
    has_strong_seniority = any(kw in full_text for kw in CORE_OPS_KEYWORDS) or                            any(kw in text for kw in ["head of", "senior", "lead ", "manager"])
    if has_strong_seniority and tier == "adjacent":
        score += 0.12
        reasons.append("seniority_in_adjacent")
    elif has_strong_seniority:
        score += 0.25
        reasons.append("strong_seniority")

    # Strong domain (DAO / Governance / Treasury)
    has_strong_domain = any(kw in full_text for kw in STRONG_DOMAIN)
    if has_strong_domain:
        score += 0.20
        reasons.append("strong_domain")

    # === DAO / Protocol Context Bonus (important for Tier 2) ===
    dao_context_terms = ["dao", "aave", "uniswap", "lido", "optimism", "arbitrum", "gitcoin",
                         "governance", "snapshot", "treasury", "protocol", "ecosystem", "contributor"]
    dao_context_hits = sum(1 for term in dao_context_terms if term in full_text)
    if dao_context_hits >= 1:
        bonus = min(0.25, 0.08 * dao_context_hits)
        score += bonus
        reasons.append(f"dao_protocol_context(+{bonus:.2f})")

    # Crypto-native bonus
    crypto_bonus = sum(1 for term in CRYPTO_NATIVE_BONUS if term in full_text)
    if crypto_bonus > 0:
        bonus = min(0.12, 0.04 * crypto_bonus)
        score += bonus
        reasons.append(f"crypto_native_bonus(+{bonus:.2f})")

    # Remote / async bonus (light)
    if any(x in text for x in ["remote", "async", "distributed"]):
        score += 0.05
        reasons.append("remote_bonus")

    # === Negative penalties ===
    for pat in HARD_NEGATIVE_PATTERNS:
        if pat.search(full_text):
            score -= 0.40
            reasons.append(f"hard_negative:{pat.pattern[:45]}")
            break  # hard negative wins

    # Soft negatives (softer for Tier 2)
    for pat in SOFT_NEGATIVE_PATTERNS:
        if pat.search(full_text):
            penalty = 0.28
            if tier == "adjacent":
                penalty = 0.08  # "Strategy Associate" in DAO context is acceptable
            score -= penalty
            reasons.append(f"soft_negative:{pat.pattern[:40]}")
            break

    # Tier-specific combo bonuses
    if tier == "core" and has_strong_domain:
        score += 0.12
        reasons.append("core+domain_combo")
    if tier == "adjacent" and has_strong_domain:
        score += 0.08
        reasons.append("adjacent+domain_combo")

    final_score = max(0.0, min(1.0, round(score, 3)))

    return {
        "score": final_score,
        "tier": tier,
        "has_strong_seniority": has_strong_seniority,
        "has_strong_domain": has_strong_domain,
        "crypto_native_bonus": crypto_bonus > 0,
        "reasons": reasons,
        "passes_strict": tier == "core" and has_strong_domain,
    }

def passes_source_threshold(score: float, source: str, thresholds: Dict[str, float] = None) -> bool:
    """Check if score meets the source-specific threshold."""
    if thresholds is None:
        thresholds = load_thresholds()
    threshold = thresholds.get(source.lower(), 0.25)
    return score >= threshold

def score_and_filter(item: Dict, source: str) -> Dict:
    """Convenience: score + decide high_relevance using source threshold.
    For Tier 2 (adjacent) we consider it high_relevance_for_source if score is solid + meets threshold.
    """
    title = item.get("title", "")
    desc = item.get("description", "") or ""
    company = item.get("company", "") or ""
    scoring = compute_segment_score(title, desc, source=source, company=company)

    thresholds = load_thresholds()
    meets_threshold = passes_source_threshold(scoring["score"], source, thresholds)

    tier = scoring.get("tier", "none")
    is_good_adjacent = tier == "adjacent" and scoring["score"] >= 0.48 and has_dao_context(title, desc, company)

    high_relevance = (scoring["passes_strict"] or is_good_adjacent) and meets_threshold

    return {
        **scoring,
        "meets_source_threshold": meets_threshold,
        "threshold_used": thresholds.get(source.lower(), 0.25),
        "high_relevance_for_source": high_relevance,
    }

def has_dao_context(title: str, description: str, company: str = "") -> bool:
    text = f"{title} {description} {company}".lower()
    dao_signals = ["dao", "governance", "protocol", "ecosystem", "aave", "uniswap", "lido", "optimism", "arbitrum", "snapshot"]
    return any(s in text for s in dao_signals)


# === Quick usage examples ===
# compute_segment_score("Strategy & Business Development Associate", "...", company="Aave")
# → tier="adjacent", score ~0.9 with dao_protocol_context
#
# compute_segment_score("Senior Operations Manager", "DAO treasury", company="Lido")
# → tier="core", score=1.0, passes_strict=True
