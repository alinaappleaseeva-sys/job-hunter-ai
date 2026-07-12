"""Ashby posting API mapper."""

from __future__ import annotations

from typing import Any

from job_hunter_ai.common.models import NormalizedJobPosting
from job_hunter_ai.common.models import RawSourceRecord
from job_hunter_ai.normalization.fields.company import extract_company_domain
from job_hunter_ai.normalization.fields.compensation import parse_ashby_compensation
from job_hunter_ai.normalization.fields.description import pick_description
from job_hunter_ai.normalization.fields.employment import normalize_employment_type
from job_hunter_ai.normalization.fields.enrichment import infer_market
from job_hunter_ai.normalization.fields.enrichment import infer_seniority
from job_hunter_ai.normalization.fields.location import parse_location_string
from job_hunter_ai.normalization.fields.remote import normalize_remote_mode
from job_hunter_ai.normalization.fields.title import normalize_title
from job_hunter_ai.normalization.mappers._helpers import company_name_from_record
from job_hunter_ai.normalization.mappers._helpers import finalize_parse_status
from job_hunter_ai.normalization.mappers._helpers import parse_iso_timestamp
from job_hunter_ai.normalization.mappers._helpers import posting_shell
from job_hunter_ai.normalization.mappers._helpers import resolve_role_family
from job_hunter_ai.normalization.mappers.base import BaseMapper


class AshbyMapper(BaseMapper):
    provider = "ashby"

    def normalize(self, record: RawSourceRecord) -> NormalizedJobPosting:
        job = record.payload or {}
        posting = posting_shell(record)
        warnings: list[str] = []

        title_raw, title_normalized = normalize_title(job.get("title"))
        posting.title_raw = title_raw
        posting.title_normalized = title_normalized

        posting.company_name = company_name_from_record(record)
        posting.company_domain = extract_company_domain(record.source_url)

        description_raw, description_text = pick_description(
            job.get("descriptionHtml"),
            job.get("descriptionPlain"),
        )
        posting.description_raw = description_raw
        posting.description_text = description_text

        location_raw = job.get("location")
        if isinstance(location_raw, str):
            location_raw = location_raw.strip() or None
        else:
            location_raw = None
        posting.location_raw = location_raw

        parsed_location = parse_location_string(location_raw)
        posting.location_country = parsed_location.location_country
        posting.location_region = parsed_location.location_region
        posting.location_city = parsed_location.location_city

        posting.remote_mode = normalize_remote_mode(
            workplace_type=job.get("workplaceType"),
            is_remote=job.get("isRemote"),
            location_raw=location_raw,
        )

        posting.employment_type = normalize_employment_type(job.get("employmentType"))
        if posting.employment_type is None:
            warnings.append("employment_type_missing")

        department = job.get("department")
        if isinstance(department, str):
            department = department.strip() or None
        else:
            department = None

        posting.seniority = infer_seniority(title_raw)
        posting.role_family = resolve_role_family(title_raw, department=department)
        posting.market = infer_market(posting.company_name, title=title_raw)

        compensation = parse_ashby_compensation(job.get("compensation"))
        posting.compensation_min = compensation.compensation_min
        posting.compensation_max = compensation.compensation_max
        posting.compensation_currency = compensation.compensation_currency
        if job.get("compensation") and compensation.compensation_min is None:
            warnings.append("compensation_unparsed")

        posting.posted_at = parse_iso_timestamp(job.get("publishedAt"))

        status, warnings = finalize_parse_status(posting, warnings)
        posting.parse_status = status
        posting.parse_warnings = warnings
        return posting