"""Basic hard requirements extraction (Phase 1 quality).

Focus on credentials and strong "must have" signals that are easy to mismatch
for a Web3 Head of Ops / DAO Ops profile (e.g. CPA, Big 4, heavy SOX/GAAP).
"""

import re
from typing import Any

# Known hard credential patterns (case-insensitive)
_CREDENTIAL_PATTERNS = [
    (re.compile(r"\bCPA\b", re.I), "CPA"),
    (re.compile(r"\bBig\s*4\b", re.I), "Big 4"),
    (re.compile(r"public accounting", re.I), "public accounting"),
    (re.compile(r"\bSOX\b", re.I), "SOX"),
    (re.compile(r"U\.?S\.?\s*GAAP", re.I), "U.S. GAAP"),
    (re.compile(r"certified public accountant", re.I), "CPA"),
]

# Strong accounting/finance ops requirement phrases
_ACCOUNTING_HEAVY = re.compile(
    r"\b(?:accounting|GL|general ledger|financial close|intercompany|SOX|GAAP)\b.*\b(?:experience|required|must|mandatory)\b",
    re.I
)


def extract_hard_requirements(text: str | None) -> dict[str, Any]:
    """Extract obvious hard credential / license signals from JD text.

    Returns a small dict suitable for scoring/penalties.
    This is intentionally conservative (high precision, lower recall) for MVP.
    """
    if not text:
        return {"credentials": [], "requires_accounting_credential": False, "raw_signals": []}

    credentials = []
    signals = []

    for pattern, label in _CREDENTIAL_PATTERNS:
        if pattern.search(text):
            if label not in credentials:
                credentials.append(label)
            signals.append(f"credential:{label}")

    if _ACCOUNTING_HEAVY.search(text):
        signals.append("accounting_heavy_requirement")
        # If we saw accounting-heavy language + credential, mark it
        if credentials:
            signals.append("accounting_credential_required")

    requires_accounting_credential = bool(credentials) or "accounting_heavy_requirement" in signals

    return {
        "credentials": credentials,
        "requires_accounting_credential": requires_accounting_credential,
        "raw_signals": signals,
    }


def has_hard_credential_mismatch(requirements: dict[str, Any], profile_has_cpa: bool = False) -> bool:
    """Simple mismatch detector.

    For our profile (no CPA/Big4 background), any clear accounting credential
    requirement is a mismatch.
    """
    if not requirements:
        return False
    if requirements.get("requires_accounting_credential") and not profile_has_cpa:
        return True
    return False
