"""Unit + eval tests for ranking v1 (Phase 6).

Covers:
- dataset load for ranking_topk
- placeholder interface for rank_jobs(profile, jobs)
- top-k precision computation skeleton
- baseline comparison skeleton
- explanation presence checks

Until ranking pipeline is implemented these tests validate data shape and will be
extended with real assertions + gate checks in the ranking-pipeline subtask.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

RANKING_GOLD_PATH = Path("evals/datasets/ranking_topk/examples.jsonl")


def _load_ranking_examples() -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    with RANKING_GOLD_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


GOLD_EXAMPLES = _load_ranking_examples()


def test_ranking_gold_dataset_loads_and_has_minimum_examples():
    """Smoke: dataset exists, parseable, has expected count and structure."""
    assert len(GOLD_EXAMPLES) >= 8
    for ex in GOLD_EXAMPLES:
        assert "example_id" in ex
        assert "profile" in ex
        assert isinstance(ex["profile"], dict)
        assert "jobs" in ex
        assert isinstance(ex["jobs"], list)
        assert len(ex["jobs"]) >= 3
        for j in ex["jobs"]:
            assert "canonical_job_id" in j or "posting_id" in j
            assert "title_normalized" in j or "title" in j
            assert "relevance_label" in j
            assert j["relevance_label"] in {"highly_relevant", "relevant", "neutral", "irrelevant"}


def test_ranking_gold_has_varied_profiles():
    """Basic diversity check on profiles in gold."""
    profile_ids = {ex["profile"].get("profile_id") for ex in GOLD_EXAMPLES}
    assert len(profile_ids) >= 5


@pytest.mark.skip(reason="ranking pipeline + rank_jobs not implemented yet (Phase 6 next subtask)")
def test_rank_jobs_interface_and_topk_precision():
    """Once implemented:

    from job_hunter_ai.ranking import rank_jobs, CandidateProfile
    ...

    for ex in GOLD_EXAMPLES:
        profile = CandidateProfile(**ex["profile"])  # or from_dict
        jobs = ... build CanonicalJob list from ex["jobs"]
        ranked = rank_jobs(profile, jobs)
        # compute precision@3
        # assert explanations
    """
    pytest.skip("implement rank_jobs + models first")


def test_ranking_suite_yaml_exists():
    """Suite definition must exist for CI gate."""
    suite_path = Path("evals/suites/ranking_topk.yaml")
    assert suite_path.exists()
    content = suite_path.read_text()
    assert "precision_at_3" in content
    assert "ranking_topk" in content
