"""Title/company enrichment heuristics (seniority, role family, market)."""

from __future__ import annotations

import re


# Negative patterns — roles that look like "ops" but are not relevant for our target profile
# (e.g. pure accounting, GL, tax, audit, SOX-heavy finance ops).
# These should NOT match our target_role_families (operations, dao_ops, etc.).
_NEGATIVE_ROLE_PATTERNS = [
    re.compile(r"\b(?:accounting|accountant|gl |general ledger|tax|audit|sox|cpa|big 4|public accounting|financial reporting|intercompany|close process|reconciliation|payroll|bookkeeper)\b", re.I),
    re.compile(r"\b(?:finance ops|financial ops|fp&a|treasury accounting)\b", re.I),
]

_SENIORITY_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(?:head|vp|vice president)\b", re.I), "head"),
    (re.compile(r"\b(?:director|manager|mgr)\b", re.I), "lead"),
    (re.compile(r"\b(?:staff|principal|distinguished)\b", re.I), "senior"),
    (re.compile(r"\bsenior\b", re.I), "senior"),
    (re.compile(r"\blead\b", re.I), "lead"),
    (re.compile(r"\b(?:junior|jr)\b", re.I), "junior"),
    (re.compile(r"\b(?:intern|internship)\b", re.I), "junior"),
]

_ROLE_FAMILY_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(?:engineer|engineering|developer|swe|sde)\b", re.I), "engineering"),
    (re.compile(r"\b(?:designer|design)\b", re.I), "design"),
    (re.compile(r"\b(?:product manager|product owner|product)\b", re.I), "product"),
    (re.compile(r"\b(?:account executive|sales|account director|ae)\b", re.I), "sales"),
    (re.compile(r"\b(?:data scientist|analytics|data)\b", re.I), "data"),
    (re.compile(r"\b(?:growth|marketing)\b", re.I), "growth"),
    (re.compile(r"\b(?:chief of staff)\b", re.I), "operations"),
    (re.compile(r"\b(?:dao|governance|working group|contributor program)\b", re.I), "operations"),
    (re.compile(r"\b(?:operations|ops)\b", re.I), "operations"),
]

_COMPANY_MARKET: dict[str, str] = {
    "stripe": "fintech",
    "ashby": "saas",
    "lever": "saas",
}


def infer_seniority(title: str | None) -> str | None:
    if not title:
        return None
    for pattern, label in _SENIORITY_RULES:
        if pattern.search(title):
            return label
    return None


def infer_role_family(title: str | None, *, department: str | None = None) -> str | None:
    haystacks = [title or "", department or ""]

    # First: check negative patterns (finance/accounting ops etc.)
    for text in haystacks:
        for pat in _NEGATIVE_ROLE_PATTERNS:
            if pat.search(text):
                return "finance_ops"

    for text in haystacks:
        for pattern, label in _ROLE_FAMILY_RULES:
            if pattern.search(text):
                return label
    return None


def infer_market(company_name: str | None, *, title: str | None = None) -> str | None:
    _ = title
    if not company_name:
        return None
    return _COMPANY_MARKET.get(company_name.strip().lower())