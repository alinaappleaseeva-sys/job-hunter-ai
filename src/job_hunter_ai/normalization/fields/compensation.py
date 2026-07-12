"""Compensation parsing helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_CURRENCY_SYMBOLS: dict[str, str] = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
}

_SALARY_RANGE_RE = re.compile(
    r"(?P<cur>[$€£¥])?\s*(?P<min>\d+(?:\.\d+)?)\s*[kK]?\s*[-–—]\s*"
    r"(?P<cur2>[$€£¥])?\s*(?P<max>\d+(?:\.\d+)?)\s*[kK]?",
)


@dataclass(slots=True)
class ParsedCompensation:
    compensation_min: float | None
    compensation_max: float | None
    compensation_currency: str | None


def _scale(value: float, *, has_k_suffix: bool, raw_fragment: str) -> float:
    if has_k_suffix or "k" in raw_fragment.lower():
        return value * 1000
    return value


def parse_salary_summary_text(text: str | None) -> ParsedCompensation:
    """Parse human-readable salary summaries like ``€76K - €185K``."""
    if not text or not str(text).strip():
        return ParsedCompensation(None, None, None)

    match = _SALARY_RANGE_RE.search(str(text))
    if not match:
        return ParsedCompensation(None, None, None)

    cur_symbol = match.group("cur") or match.group("cur2")
    currency = _CURRENCY_SYMBOLS.get(cur_symbol) if cur_symbol else None
    fragment = match.group(0)
    min_raw = float(match.group("min"))
    max_raw = float(match.group("max"))
    return ParsedCompensation(
        compensation_min=_scale(min_raw, has_k_suffix=True, raw_fragment=fragment),
        compensation_max=_scale(max_raw, has_k_suffix=True, raw_fragment=fragment),
        compensation_currency=currency,
    )


def parse_ashby_compensation(payload: dict[str, Any] | None) -> ParsedCompensation:
    """Extract salary range from Ashby ``compensation`` object."""
    if not payload or not isinstance(payload, dict):
        return ParsedCompensation(None, None, None)

    summary = payload.get("scrapeableCompensationSalarySummary")
    if isinstance(summary, str) and summary.strip():
        parsed = parse_salary_summary_text(summary)
        if parsed.compensation_min is not None:
            return parsed

    components = payload.get("summaryComponents")
    if isinstance(components, list):
        for component in components:
            if not isinstance(component, dict):
                continue
            if component.get("compensationType") != "Salary":
                continue
            currency = component.get("currencyCode")
            min_val = component.get("minValue")
            max_val = component.get("maxValue")
            return ParsedCompensation(
                compensation_min=float(min_val) if min_val is not None else None,
                compensation_max=float(max_val) if max_val is not None else None,
                compensation_currency=str(currency) if currency else None,
            )

    tiers = payload.get("compensationTiers")
    if isinstance(tiers, list):
        for tier in tiers:
            if not isinstance(tier, dict):
                continue
            for component in tier.get("components") or []:
                if not isinstance(component, dict):
                    continue
                if component.get("compensationType") != "Salary":
                    continue
                currency = component.get("currencyCode")
                min_val = component.get("minValue")
                max_val = component.get("maxValue")
                return ParsedCompensation(
                    compensation_min=float(min_val) if min_val is not None else None,
                    compensation_max=float(max_val) if max_val is not None else None,
                    compensation_currency=str(currency) if currency else None,
                )

    tier_summary = payload.get("compensationTierSummary")
    if isinstance(tier_summary, str):
        return parse_salary_summary_text(tier_summary)

    return ParsedCompensation(None, None, None)