"""Ingestion smoke tests for Phase 8 new sources.

Stub until real connectors added. Validates dataset expectations.
"""

import json
from pathlib import Path
import pytest

SMOKE_DIR = Path("evals/datasets/ingestion")

def test_remoteok_smoke_exists():
    files = list(SMOKE_DIR.glob("smoke_remoteok*.jsonl"))
    assert files, "Remote OK smoke dataset missing"
    for f in files:
        data = [json.loads(line) for line in f.read_text().splitlines() if line.strip()]
        assert len(data) >= 1
        for ex in data:
            assert "records_expected_min" in ex or "source" in ex
