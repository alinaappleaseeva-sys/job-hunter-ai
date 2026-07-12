"""Normalization — raw records to ``NormalizedJobPosting``."""

from job_hunter_ai.normalization.mappers.base import BaseMapper
from job_hunter_ai.normalization.pipeline import normalize_postings
from job_hunter_ai.normalization.pipeline import normalize_record
from job_hunter_ai.normalization.registry import get_mapper
from job_hunter_ai.normalization.registry import register_mapper
from job_hunter_ai.normalization.registry import resolve_provider
from job_hunter_ai.normalization.types import NormalizationItemResult
from job_hunter_ai.normalization.types import NormalizationRunResult
from job_hunter_ai.normalization.types import ParseDiagnostics

__all__ = [
    "BaseMapper",
    "NormalizationItemResult",
    "NormalizationRunResult",
    "ParseDiagnostics",
    "get_mapper",
    "normalize_postings",
    "normalize_record",
    "register_mapper",
    "resolve_provider",
]