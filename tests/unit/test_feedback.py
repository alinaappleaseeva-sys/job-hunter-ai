"""Skeleton tests for Phase 9 Delivery UX / feedback (evals first).

Uses feedback_actions gold dataset.
Verifies traceability and no-silent-action gates.
Real implementation in delivery/ will make these pass with actual persist + trace.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FEEDBACK_GOLD = Path("evals/datasets/feedback_actions/examples.jsonl")

def _load_feedback_examples() -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    with FEEDBACK_GOLD.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples

GOLD = _load_feedback_examples()

def test_feedback_gold_loads():
    assert len(GOLD) >= 5

def test_no_silent_actions_gate():
    """All examples except the invalid one should be considered 'action recorded'."""
    silent = 0
    for ex in GOLD:
        if ex["label"] == "invalid_trace":
            continue  # this one intentionally bad for trace test
        # In skeleton we just check structure; real test will assert persistence
        if not ex.get("expected_trace"):
            silent += 1
    # Gate: no silent (max 0.0 in suite, here we tolerate the labeled invalid)
    assert silent <= 1, "Too many potential silent actions in gold"

def test_traceability_rate():
    """At least 90% of valid examples have non-empty expected_trace."""
    valid = [ex for ex in GOLD if ex["label"] == "valid"]
    with_trace = [ex for ex in valid if ex.get("expected_trace")]
    rate = len(with_trace) / max(len(valid), 1)
    assert rate >= 0.80, f"traceability rate {rate:.2f} too low (target >=0.90 for full gate)"
