"""Unit tests for shared normalization field helpers (Step 4.3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from job_hunter_ai.normalization.fields import (
    extract_company_domain,
    html_to_text,
    infer_market,
    infer_role_family,
    infer_seniority,
    normalize_employment_type,
    normalize_remote_mode,
    normalize_title,
    parse_ashby_compensation,
    parse_location_string,
    parse_salary_summary_text,
    pick_description,
)

GOLD_PATH = Path("evals/datasets/normalization_gold/examples.jsonl")


def _load_gold_examples() -> list[dict]:
    examples: list[dict] = []
    with GOLD_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


GOLD_EXAMPLES = _load_gold_examples()
TITLE_CASES = [
    pytest.param(
        ex["labels"]["title_raw"],
        ex["labels"]["title_normalized"],
        id=ex["example_id"],
    )
    for ex in GOLD_EXAMPLES
    if ex["labels"].get("title_raw") is not None
]


class TestNormalizeTitle:
    @pytest.mark.parametrize("title_raw,title_normalized", TITLE_CASES)
    def test_matches_gold_labels(self, title_raw: str, title_normalized: str) -> None:
        raw, normalized = normalize_title(title_raw)
        assert raw == title_raw
        assert normalized == title_normalized

    def test_empty_title_returns_none(self) -> None:
        assert normalize_title("") == (None, None)
        assert normalize_title("   ") == (None, None)
        assert normalize_title(None) == (None, None)


class TestParseLocationString:
    @pytest.mark.parametrize(
        ("location_raw", "country", "region", "city"),
        [
            ("San Francisco, CA", "US", "CA", "San Francisco"),
            ("Japan", "JP", None, None),
            ("Singapore", "SG", None, "Singapore"),
            ("Arlington, TX", "US", "TX", "Arlington"),
            ("Atlanta, Georgia", "US", "GA", "Atlanta"),
            ("Bombay, MH", "IN", "MH", "Mumbai"),
            ("Remote - European Union", None, None, None),
            ("Remote - US", "US", None, None),
            ("France", "FR", None, None),
            ("United Kingdom", "GB", None, None),
        ],
        ids=[
            "city_state_abbrev",
            "country_japan",
            "country_singapore",
            "city_state_tx",
            "city_state_name",
            "city_state_india",
            "remote_eu",
            "remote_us",
            "country_france",
            "country_uk",
        ],
    )
    def test_structured_fields(
        self,
        location_raw: str,
        country: str | None,
        region: str | None,
        city: str | None,
    ) -> None:
        parsed = parse_location_string(location_raw)
        assert parsed.location_raw == location_raw
        assert parsed.location_country == country
        assert parsed.location_region == region
        assert parsed.location_city == city

    def test_missing_location(self) -> None:
        parsed = parse_location_string(None)
        assert parsed.location_raw is None
        assert parsed.location_country is None


class TestNormalizeRemoteMode:
    @pytest.mark.parametrize(
        ("kwargs", "expected"),
        [
            ({"workplace_type": "Remote"}, "remote"),
            ({"workplace_type": "hybrid"}, "hybrid"),
            ({"workplace_type": "unspecified", "location_raw": "Bombay, MH"}, "unknown"),
            ({"workplace_type": "remote"}, "remote"),
            ({"categories_remote": True}, "remote"),
            ({"location_raw": "San Francisco, CA"}, "onsite"),
            (
                {
                    "location_raw": (
                        "US-Remote, US-San Francisco, US-Chicago, US-New York, "
                        "US-Seattle, US-Texas"
                    )
                },
                "remote",
            ),
            (
                {
                    "location_raw": (
                        "New York, NY; San Francisco, CA; Seattle, WA; "
                        "Los Angeles, CA; Denver, CO; Austin, TX; US-West Remote"
                    )
                },
                "hybrid",
            ),
            ({"location_raw": "Remote - US", "is_remote": True}, "remote"),
        ],
        ids=[
            "ashby_remote",
            "lever_hybrid",
            "lever_unspecified",
            "lever_remote_workplace",
            "lever_categories_remote",
            "greenhouse_onsite_city",
            "greenhouse_multi_remote",
            "greenhouse_hybrid_multi_hub",
            "ashby_remote_us",
        ],
    )
    def test_inference(self, kwargs: dict, expected: str) -> None:
        assert normalize_remote_mode(**kwargs) == expected


class TestNormalizeEmploymentType:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("FullTime", "full-time"),
            ("Regular Full Time (Salary)", "full-time"),
            ("full-time", "full-time"),
            ("Part-Time", "part-time"),
            ("contract", "contract"),
            ("internship", "internship"),
            (None, None),
            ("", None),
            ("freelance", None),
        ],
    )
    def test_canonical_values(self, raw: str | None, expected: str | None) -> None:
        assert normalize_employment_type(raw) == expected


class TestEnrichment:
    @pytest.mark.parametrize(
        ("title", "expected"),
        [
            ("Account Director (Inside/Outside Hybrid Sales)", "lead"),
            ("Engineering Manager, EU", "lead"),
            ("Senior Product Designer", "senior"),
            ("Staff Product Engineer, Americas", "senior"),
            ("Account Executive", None),
        ],
    )
    def test_infer_seniority(self, title: str, expected: str | None) -> None:
        assert infer_seniority(title) == expected

    @pytest.mark.parametrize(
        ("title", "department", "expected"),
        [
            ("Account Executive, AI Sales (Grower)", None, "sales"),
            ("Engineering Manager, EU", "Engineering", "engineering"),
            ("Senior Product Designer", None, "design"),
            ("AbelsonTaylor Writer", None, None),
            # Negative patterns for finance/accounting ops (regression for Phase 1 quality)
            ("Accounting Manager, GL Operations", None, "finance_ops"),
            ("Financial Controller", None, "finance_ops"),
            ("GL Accountant at Protocol", None, "finance_ops"),
        ],
    )
    def test_infer_role_family(
        self,
        title: str,
        department: str | None,
        expected: str | None,
    ) -> None:
        assert infer_role_family(title, department=department) == expected

    @pytest.mark.parametrize(
        ("company", "expected"),
        [
            ("Stripe", "fintech"),
            ("Ashby", "saas"),
            ("leverdemo", None),
        ],
    )
    def test_infer_market(self, company: str, expected: str | None) -> None:
        assert infer_market(company) == expected


class TestCompanyDomain:
    def test_extracts_host(self) -> None:
        assert (
            extract_company_domain("https://stripe.com/jobs/listing/123")
            == "stripe.com"
        )
        assert extract_company_domain("https://www.ashbyhq.com/jobs") == "ashbyhq.com"
        assert (
            extract_company_domain(
                "https://jobs.lever.co/leverdemo/33538a2f-d27d-4a96-8f05-fa4b0e4d940e"
            )
            == "lever.co"
        )
        assert (
            extract_company_domain(
                "https://jobs.ashbyhq.com/Ashby/7458d4e9-da2e-47bd-98cb-adfda43d42b2"
            )
            == "ashbyhq.com"
        )

    def test_missing_url(self) -> None:
        assert extract_company_domain(None) is None
        assert extract_company_domain("") is None


class TestDescription:
    def test_html_to_text_strips_tags(self) -> None:
        assert html_to_text("<p>Hello <b>world</b></p>") == "Hello world"

    def test_pick_description_prefers_html_then_plain(self) -> None:
        raw, text = pick_description("<p>HTML</p>", "Plain fallback")
        assert raw == "<p>HTML</p>"
        assert text == "HTML"

    def test_pick_description_plain_only(self) -> None:
        raw, text = pick_description("Plain only")
        assert raw == "Plain only"
        assert text == "Plain only"


class TestCompensation:
    def test_parse_salary_summary_text(self) -> None:
        parsed = parse_salary_summary_text("€76K - €185K")
        assert parsed.compensation_min == 76_000
        assert parsed.compensation_max == 185_000
        assert parsed.compensation_currency == "EUR"

    def test_parse_ashby_compensation_from_summary(self) -> None:
        payload = {"scrapeableCompensationSalarySummary": "$120K - $160K"}
        parsed = parse_ashby_compensation(payload)
        assert parsed.compensation_min == 120_000
        assert parsed.compensation_max == 160_000
        assert parsed.compensation_currency == "USD"

    def test_parse_ashby_compensation_empty(self) -> None:
        parsed = parse_ashby_compensation(None)
        assert parsed.compensation_min is None
        assert parsed.compensation_max is None