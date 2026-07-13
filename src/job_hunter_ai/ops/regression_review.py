"""Eval regression review routine (Phase 10 skeleton).

Provides a checklist + simple diff reporter that can be called after material changes.
"""

from __future__ import annotations

from typing import Any


REGRESSION_CHECKLIST = [
    "Run ranking_topk suite and compare precision@3 / explanation coverage",
    "Run ghosting_precision and check FP rate + catch rate",
    "Run ingestion_smoke + dedup_regression on new sources",
    "Run phase10_operational gates (health + telegram noise)",
    "If precision@3 drops > 5% or new FP > 3pp → block or add mitigation",
    "Document post-change eval summary in PR description",
]


def generate_regression_review_summary(
    before: dict[str, float],
    after: dict[str, float],
    change_description: str,
) -> dict[str, Any]:
    """Minimal regression review summary generator."""
    report = {
        "change": change_description,
        "before": before,
        "after": after,
        "deltas": {},
        "recommendation": "review_required",
        "checklist": REGRESSION_CHECKLIST,
    }
    for k in before:
        if k in after:
            report["deltas"][k] = round(after[k] - before[k], 4)
    p3_delta = report["deltas"].get("precision_at_3", 0)
    if p3_delta < -0.05:
        report["recommendation"] = "block_or_mitigate"
    elif p3_delta < -0.02:
        report["recommendation"] = "add_explanation_and_rerun"
    else:
        report["recommendation"] = "ok_with_summary"
    return report


def print_regression_report(report: dict[str, Any]) -> None:
    print("=== Eval Regression Review ===")
    print(f"Change: {report['change']}")
    print(f"Recommendation: {report['recommendation']}")
    print("Deltas:", report["deltas"])
    print("Checklist items to complete:")
    for item in report["checklist"]:
        print(f"  - {item}")
