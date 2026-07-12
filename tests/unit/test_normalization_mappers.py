"""Unit tests for ATS normalization mappers (Step 4.4)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.connectors.ashby import AshbyConnector
from job_hunter_ai.connectors.greenhouse import GreenhouseConnector
from job_hunter_ai.connectors.lever import LeverConnector
from job_hunter_ai.normalization import normalize_record
from job_hunter_ai.normalization.mappers import register_default_mappers
from job_hunter_ai.normalization.registry import registered_providers

NOW = datetime(2026, 7, 12, tzinfo=timezone.utc)
GOLD_PATH = Path("evals/datasets/normalization_gold/examples.jsonl")


def _load_gold() -> list[dict]:
    rows: list[dict] = []
    with GOLD_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _greenhouse_record(index: int, *, board_token: str = "stripe") -> RawSourceRecord:
    jobs = json.loads(
        Path("tests/fixtures/greenhouse/greenhouse_job_board.json").read_text(encoding="utf-8")
    )["jobs"]
    connector = GreenhouseConnector(board_token)
    return connector._to_record(jobs[index], fetched_at=NOW, meta={})


def _lever_record(index: int, *, site: str = "leverdemo") -> RawSourceRecord:
    jobs = json.loads(Path("tests/fixtures/lever/leverdemo.json").read_text(encoding="utf-8"))
    connector = LeverConnector(site)
    return connector._to_record(jobs[index], fetched_at=NOW)


def _ashby_record(index: int, *, client_name: str = "Ashby") -> RawSourceRecord:
    jobs = json.loads(
        Path("tests/fixtures/ashby/ashby_job_board.json").read_text(encoding="utf-8")
    )["jobs"]
    connector = AshbyConnector(client_name)
    return connector._to_record(jobs[index], fetched_at=NOW, api_version="1")


def _record_for_example(example: dict) -> RawSourceRecord | None:
    if example.get("synthetic"):
        payload = example.get("synthetic_payload") or {}
        return RawSourceRecord(
            source_name=example["source_name"],
            source_type=example["source_type"],
            record_type="job_posting",
            external_id=str(payload.get("id")) if payload.get("id") is not None else None,
            source_url=None,
            fetched_at=NOW,
            discovered_at=None,
            payload=payload,
            content_hash="synthetic",
            cursor_value=None,
            metadata={"provider": example["provider"]},
        )

    index = example["fixture_index"]
    provider = example["provider"]
    if provider == "greenhouse":
        return _greenhouse_record(index)
    if provider == "lever":
        return _lever_record(index)
    if provider == "ashby":
        return _ashby_record(index)
    return None


def _grade_field(predicted: object, label: object, mode: str) -> bool:
    if mode == "exact":
        return predicted == label
    if mode == "enum":
        return predicted == label
    if mode == "absent":
        return predicted is None or predicted == ""
    if mode == "present":
        return predicted is not None and predicted != ""
    if mode == "contains":
        if predicted is None or label is None:
            return False
        return str(label) in str(predicted) or str(predicted) in str(label)
    if mode == "warning_superset":
        predicted_warnings = predicted if isinstance(predicted, list) else []
        label_warnings = label if isinstance(label, list) else []
        return all(w in predicted_warnings for w in label_warnings)
    raise ValueError(f"Unknown grading mode: {mode}")


@pytest.fixture(autouse=True)
def _setup_mappers() -> None:
    from job_hunter_ai.normalization import registry

    registry._MAPPERS.clear()
    register_default_mappers()
    yield
    registry._MAPPERS.clear()


def test_register_default_mappers_registers_all_providers() -> None:
    assert registered_providers() == frozenset({"greenhouse", "lever", "ashby"})


@pytest.mark.parametrize("example", [ex for ex in _load_gold() if not ex.get("synthetic")])
def test_gold_fixture_examples_match_graded_fields(example: dict) -> None:
    record = _record_for_example(example)
    assert record is not None

    item = normalize_record(record)
    posting = item.posting
    labels = example["labels"]
    grading = example.get("grading", {})

    for field_name, mode in grading.items():
        predicted = getattr(posting, field_name, None)
        label = labels.get(field_name)
        assert _grade_field(predicted, label, mode), (
            f"{example['example_id']} field={field_name} mode={mode} "
            f"predicted={predicted!r} label={label!r}"
        )


def test_synthetic_empty_title_fails() -> None:
    example = next(ex for ex in _load_gold() if ex["example_id"] == "norm-syn-001")
    record = _record_for_example(example)
    assert record is not None

    item = normalize_record(record)
    assert item.posting.parse_status == "failed"
    assert "title_missing" in item.posting.parse_warnings


def test_greenhouse_stripe_example_partial_status() -> None:
    item = normalize_record(_greenhouse_record(0))
    posting = item.posting
    assert posting.parse_status == "partial"
    assert posting.title_normalized == "account executive, ai sales (grower)"
    assert posting.company_name == "Stripe"
    assert posting.company_domain == "stripe.com"
    assert posting.remote_mode == "onsite"
    assert "employment_type_missing" in posting.parse_warnings


def test_lever_parsed_example_has_full_time() -> None:
    item = normalize_record(_lever_record(1))
    posting = item.posting
    assert posting.parse_status == "parsed"
    assert posting.employment_type == "full-time"
    assert posting.seniority == "lead"
    assert posting.role_family == "sales"


def test_ashby_engineering_manager_parsed() -> None:
    item = normalize_record(_ashby_record(0))
    posting = item.posting
    assert posting.parse_status == "parsed"
    assert posting.employment_type == "full-time"
    assert posting.remote_mode == "remote"
    assert posting.role_family == "engineering"
    assert posting.seniority == "lead"
    assert posting.company_domain == "ashbyhq.com"