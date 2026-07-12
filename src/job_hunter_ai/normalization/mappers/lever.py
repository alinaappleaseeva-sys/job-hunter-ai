"""Lever Postings API mapper."""

from __future__ import annotations

from typing import Any

from job_hunter_ai.common.models import NormalizedJobPosting
from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.normalization.fields.company import extract_company_domain
from job_hunter_ai.normalization.fields.description import pick_description
from job_hunter_ai.normalization.fields.employment import normalize_employment_type
from job_hunter_ai.normalization.fields.enrichment import infer_market
from job_hunter_ai.normalization.fields.enrichment import infer_seniority
from job_hunter_ai.normalization.fields.location import parse_location_string
from job_hunter_ai.normalization.fields.remote import normalize_remote_mode
from job_hunter_ai.normalization.fields.title import normalize_title
from job_hunter_ai.normalization.mappers._helpers import company_name_from_record
from job_hunter_ai.normalization.mappers._helpers import finalize_parse_status
from job_hunter_ai.normalization.mappers._helpers import parse_lever_timestamp
from job_hunter_ai.normalization.mappers._helpers import posting_shell
from job_hunter_ai.normalization.mappers._helpers import resolve_role_family
from job_hunter_ai.normalization.mappers.base import BaseMapper


class LeverMapper(BaseMapper):
    provider = "lever"

    def normalize(self, record: RawSourceRecord) -> NormalizedJobPosting:
        job = record.payload or {}
        posting = posting_shell(record)
        warnings: list[str] = []

        title_raw, title_normalized = normalize_title(job.get("text") or job.get("title"))
        posting.title_raw = title_raw
        posting.title_normalized = title_normalized

        posting.company_name = company_name_from_record(record)
        posting.company_domain = extract_company_domain(record.source_url)

        description_raw, description_text = pick_description(
            job.get("descriptionHtml"),
            job.get("descriptionPlain"),
            job.get("description"),
        )
        posting.description_raw = description_raw
        posting.description_text = description_text

        categories = job.get("categories") if isinstance(job.get("categories"), dict) else {}
        location_raw = _lever_location(categories)
        posting.location_raw = location_raw
        if not location_raw:
            warnings.append("location_missing")

        parsed_location = parse_location_string(location_raw)
        posting.location_country = parsed_location.location_country
        posting.location_region = parsed_location.location_region
        posting.location_city = parsed_location.location_city

        posting.remote_mode = normalize_remote_mode(
            workplace_type=job.get("workplaceType"),
            categories_remote=categories.get("remote"),
            location_raw=location_raw,
        )

        employment_raw = categories.get("commitment")
        posting.employment_type = normalize_employment_type(
            str(employment_raw) if employment_raw is not None else None
        )
        if posting.employment_type is None:
            warnings.append("employment_type_missing")

        department = categories.get("department")
        if isinstance(department, str):
            department = department.strip() or None
        else:
            department = None

        posting.seniority = infer_seniority(title_raw)
        posting.role_family = resolve_role_family(title_raw, department=department)
        posting.market = infer_market(posting.company_name, title=title_raw)

        posting.posted_at = parse_lever_timestamp(job.get("createdAt")) or parse_lever_timestamp(
            job.get("publishedAt")
        )

        status, warnings = finalize_parse_status(posting, warnings)
        posting.parse_status = status
        posting.parse_warnings = warnings
        return posting


def _lever_location(categories: dict[str, Any]) -> str | None:
    location = categories.get("location")
    if isinstance(location, str) and location.strip():
        return location.strip()
    all_locations = categories.get("allLocations")
    if isinstance(all_locations, list):
        for item in all_locations:
            if isinstance(item, str) and item.strip():
                return item.strip()
    return None