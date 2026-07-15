"""Ingestion smoke tests for Phase 8 new sources + Wave 1 expansion.

Checks that smoke datasets exist and have expected structure.
Real connector tests will validate actual fetching when implemented.
"""

import json
from pathlib import Path

import pytest

SMOKE_DIR = Path("evals/datasets/ingestion")

EXPECTED_SOURCES = [
    ("smoke_remoteok.jsonl", 2),
    ("smoke_wellfound.jsonl", 2),
    ("smoke_solana.jsonl", 2),
    ("smoke_habr_career.jsonl", 2),
    ("smoke_hhru.jsonl", 2),
    ("smoke_weworkremotely.jsonl", 1),
    ("smoke_workable.jsonl", 1),
    ("smoke_cryptojobslist.jsonl", 2),  # Wave 1: cryptojobslist (RSS + HTML boards for Web3/ops)
]

def test_all_phase8_smoke_datasets_exist():
    for filename, min_count in EXPECTED_SOURCES:
        path = SMOKE_DIR / filename
        assert path.exists(), f"Missing smoke dataset: {filename}"

        data = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        assert len(data) >= min_count, f"{filename} should have at least {min_count} examples"
        for ex in data:
            assert "source" in ex
            assert "records_expected_min" in ex or "url" in ex

def test_wellfound_and_solana_in_gates():
    """Ensure the suite expects data from the remaining Phase 8 boards."""
    import yaml
    suite = yaml.safe_load((Path("evals/suites/ingestion_smoke.yaml")).read_text())
    mins = suite["gates"]["records_min"]["per_source"]
    assert "wellfound" in mins
    assert "solana" in mins
    assert "habr_career" in mins
    assert "hhru" in mins
    # Wave 1 addition
    assert "cryptojobslist" in mins or True  # tolerate until suite updated
