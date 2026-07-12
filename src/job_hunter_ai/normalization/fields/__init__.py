"""Shared field normalizers used by provider mappers."""

from job_hunter_ai.normalization.fields.company import extract_company_domain
from job_hunter_ai.normalization.fields.compensation import ParsedCompensation
from job_hunter_ai.normalization.fields.compensation import parse_ashby_compensation
from job_hunter_ai.normalization.fields.compensation import parse_salary_summary_text
from job_hunter_ai.normalization.fields.description import html_to_text
from job_hunter_ai.normalization.fields.description import pick_description
from job_hunter_ai.normalization.fields.employment import normalize_employment_type
from job_hunter_ai.normalization.fields.enrichment import infer_market
from job_hunter_ai.normalization.fields.enrichment import infer_role_family
from job_hunter_ai.normalization.fields.enrichment import infer_seniority
from job_hunter_ai.normalization.fields.location import ParsedLocation
from job_hunter_ai.normalization.fields.location import parse_location_string
from job_hunter_ai.normalization.fields.remote import normalize_remote_mode
from job_hunter_ai.normalization.fields.title import normalize_title

__all__ = [
    "ParsedCompensation",
    "ParsedLocation",
    "extract_company_domain",
    "html_to_text",
    "infer_market",
    "infer_role_family",
    "infer_seniority",
    "normalize_employment_type",
    "normalize_remote_mode",
    "normalize_title",
    "parse_ashby_compensation",
    "parse_location_string",
    "parse_salary_summary_text",
    "pick_description",
]