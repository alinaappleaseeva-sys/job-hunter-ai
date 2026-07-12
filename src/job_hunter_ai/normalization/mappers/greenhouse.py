"""Greenhouse Job Board API mapper."""

from __future__ import annotations

from typing import Any

from job_hunter_ai.common.models import NormalizedJobPosting
from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.normalization.fields.company import extract_company_domain
from job_hunter_ai.normalization.fields.description import pick_description
from job_hunter_ai.normalization.fields.enrichment import infer_market
from job_hunter_ai.normalization.fields.enrichment import infer_seniority
from job_hunter_ai.normalization.fields.location import parse_location_string
from job_hunter_ai.normalization.fields.remote import normalize_remote_mode
from job_hunter_ai.normalization.fields.title import normalize_title
from job_hunter_ai.normalization.mappers._helpers import company_name_from_record
from job_hunter_ai.normalization.mappers._helpers import finalize_parse_status
from job_hunter_ai.normalization.mappers._helpers import multi_location_warning
from job_hunter_ai.normalization.mappers._helpers import parse_iso_timestamp
from job_hunter_ai.normalization.mappers._helpers import posting_shell
from job_hunter_ai.normalization.mappers._helpers import resolve_role_family
from job_hunter_ai.normalization.mappers.base import BaseMapper


class GreenhouseMapper(BaseMapper):
    provider = "greenhouse"

    def normalize(self, record: RawSourceRecord) -> NormalizedJobPosting:
        job = record.payload or {}
        posting = posting_shell(record)
        warnings: list[str] = []

        title_raw, title_normalized = normalize_title(job.get("title"))
        posting.title_raw = title_raw
        posting.title_normalized = title_normalized

        posting.company_name = company_name_from_record(record)
        posting.company_domain = extract_company_domain(record.source_url)

        description_raw, description_text = pick_description(job.get("content"))
        posting.description_raw = description_raw
        posting.description_text = description_text

        location_raw = _location_name(job.get("location"))
        posting.location_raw = location_raw
        parsed_location = parse_location_string(location_raw)
        posting.location_country = parsed_location.location_country
        posting.location_region = parsed_location.location_region
        posting.location_city = parsed_location.location_city

        posting.remote_mode = normalize_remote_mode(location_raw=location_raw)
        posting.employment_type = None
        warnings.append("employment_type_missing")

        if multi_location_warning(location_raw):
            warnings.append("multi_location")

        department = _first_department(job.get("departments"))
        posting.seniority = infer_seniority(title_raw)
        posting.role_family = resolve_role_family(title_raw, department=department)
        posting.market = infer_market(posting.company_name, title=title_raw)

        posting.posted_at = parse_iso_timestamp(job.get("first_published")) or parse_iso_timestamp(
            job.get("updated_at")
        )

        status, warnings = finalize_parse_status(posting, warnings)
        posting.parse_status = status
        posting.parse_warnings = warnings
        return posting


def _location_name(location: Any) -> str | None:
    if isinstance(location, dict):
        name = location.get("name")
        return str(name).strip() if name else None
    if isinstance(location, str) and location.strip():
        return location.strip()
    return None


def _first_department(departments: Any) -> str | None:
    if not isinstance(departments, list):
        return None
    for item in departments:
        if isinstance(item, dict) and item.get("name"):
            return str(item["name"])
    return None