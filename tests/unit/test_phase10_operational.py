"""Skeleton tests for Phase 10 operational hardening evals.

Covers source health, Telegram quality, and regression detection gates.
Real implementations will make the assertions stricter.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

BASE = Path("evals/datasets/phase10_operational")

def _load_jsonl(name: str) -> list[dict[str, Any]]:
    path = BASE / name
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items

def test_source_health_dataset():
    data = _load_jsonl("source_health.jsonl")
    assert len(data) >= 3
    healthy = [d for d in data if d["label"] == "healthy"]
    assert len(healthy) >= 1

def test_telegram_quality_dataset():
    data = _load_jsonl("telegram_quality.jsonl")
    assert len(data) >= 3
    signals = [d for d in data if d["label"] == "good_signal"]
    assert len(signals) >= 1

def test_eval_regression_dataset():
    data = _load_jsonl("eval_regression.jsonl")
    assert len(data) >= 2
    regressions = [d for d in data if d["label"] == "regression"]
    assert len(regressions) >= 1

def test_source_health_gate_skeleton():
    data = _load_jsonl("source_health.jsonl")
    healthy_rate = sum(1 for d in data if d["label"] == "healthy") / len(data)
    # Loose skeleton gate; real implementation will enforce >= 0.85 on live windows
    assert healthy_rate >= 0.4

def test_telegram_signal_rate_skeleton():
    data = _load_jsonl("telegram_quality.jsonl")
    job_signals = [d for d in data if d.get("is_job")]
    signal_rate = len(job_signals) / max(len(data), 1)
    assert signal_rate >= 0.5  # skeleton; production target higher
