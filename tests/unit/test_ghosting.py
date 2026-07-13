"""Skeleton tests for ghosting v1 (Phase 7).

Covers dataset load and basic structure.
Real scoring + gates will be added after ghosting implementation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

GHOST_GOLD_PATH = Path("evals/datasets/ghosting_precision/examples.jsonl")


def _load_ghost_examples() -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    with GHOST_GOLD_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


GOLD_EXAMPLES = _load_ghost_examples()


def test_ghosting_gold_loads_and_has_examples():
    assert len(GOLD_EXAMPLES) >= 8
    for ex in GOLD_EXAMPLES:
        assert "example_id" in ex
        assert "ghost_label" in ex
        assert ex["ghost_label"] in {"active-good", "stale", "suspicious_evergreen", "unclear"}
        assert "signals" in ex
        assert isinstance(ex["signals"], list)


def test_ghosting_suite_yaml_exists():
    suite = Path("evals/suites/ghosting_precision.yaml")
    assert suite.exists()
    content = suite.read_text()
    assert "fp_rate_on_good" in content
    assert "catch_rate_on_ghosts" in content


@pytest.mark.skip(reason="ghost scoring implementation pending (Phase 7 next subtask)")
def test_ghost_score_and_policy():
    """Will test:
    - compute_ghost_score returns (score, reasons)
    - policy decisions
    - FP rate and catch rate on gold
    """
    pytest.skip("implement ghosting module first")
