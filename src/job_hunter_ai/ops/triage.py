"""Broken-source triage flow (Phase 10 skeleton).

Minimal but usable: given health summaries, produce triage recommendations.
"""

from __future__ import annotations

from typing import Any

from job_hunter_ai.ops.source_health import SourceHealthSummary


def triage_degraded_sources(
    summaries: dict[str, SourceHealthSummary],
) -> list[dict[str, Any]]:
    """Return list of triage actions for degraded sources."""
    actions = []
    for name, s in summaries.items():
        if s.status != "degraded":
            continue
        recommendation = "pause"
        reason = []
        if s.successful_fetches / max(s.total_fetches, 1) < 0.7:
            reason.append("low fetch success")
        if s.avg_parse_quality < 0.65:
            reason.append("poor parse quality")
        if s.stale_ratio > 0.3:
            reason.append("high staleness")
        actions.append({
            "source": name,
            "status": s.status,
            "recommendation": recommendation,
            "reasons": reason or ["general degradation"],
            "suggested_action": "investigate_connector_or_source_health",
        })
    return actions


def print_triage_report(actions: list[dict[str, Any]]) -> None:
    if not actions:
        print("No degraded sources to triage.")
        return
    print("=== Broken Source Triage ===")
    for a in actions:
        print(f"- {a['source']}: {a['recommendation']} ({', '.join(a['reasons'])})")
