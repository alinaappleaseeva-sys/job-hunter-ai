"""Dedup regression tests (Phase 8 cross-family).

Loads examples and checks structure. Real dedup service tests in test_dedup_service.
"""

import json
from pathlib import Path

DEDUP_GOLD = Path("evals/datasets/dedup_regression/examples.jsonl")

def test_dedup_regression_loads():
    examples = [json.loads(l) for l in DEDUP_GOLD.read_text().splitlines() if l.strip()]
    assert len(examples) >= 3
    for ex in examples:
        assert "type" in ex
        assert ex["type"] in ("must_merge", "must_not_merge")
        assert "postings" in ex
        assert len(ex["postings"]) >= 2
