"""Rollout rules for new sources (Phase 10 skeleton)."""

from __future__ import annotations

from typing import Any


ROLLOUT_RULES = {
    "min_eval_coverage": 0.8,
    "max_noise_rate": 0.35,
    "min_precision_at_3": 0.55,
    "require_health_green": True,
}


def can_rollout_source(
    source_name: str,
    metrics: dict[str, Any],
    rules: dict[str, Any] = ROLLOUT_RULES,
) -> tuple[bool, list[str]]:
    """Return (allowed, reasons)."""
    reasons = []
    allowed = True

    if metrics.get("eval_coverage", 1.0) < rules["min_eval_coverage"]:
        allowed = False
        reasons.append("insufficient eval coverage")

    if metrics.get("noise_rate", 0.0) > rules["max_noise_rate"]:
        allowed = False
        reasons.append("noise rate too high")

    if metrics.get("precision_at_3", 1.0) < rules["min_precision_at_3"]:
        allowed = False
        reasons.append("precision@3 below threshold")

    if rules["require_health_green"] and metrics.get("health_status") != "healthy":
        allowed = False
        reasons.append("source health not green")

    return allowed, reasons or ["passes all rollout rules"]
