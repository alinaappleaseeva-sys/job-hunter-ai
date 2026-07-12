"""Provider-specific normalization mappers."""

from job_hunter_ai.normalization.mappers.ashby import AshbyMapper
from job_hunter_ai.normalization.mappers.base import BaseMapper
from job_hunter_ai.normalization.mappers.greenhouse import GreenhouseMapper
from job_hunter_ai.normalization.mappers.lever import LeverMapper
from job_hunter_ai.normalization.registry import register_mapper

__all__ = [
    "AshbyMapper",
    "BaseMapper",
    "GreenhouseMapper",
    "LeverMapper",
    "register_default_mappers",
]


def register_default_mappers() -> None:
    """Register all built-in ATS mappers."""
    for mapper in (GreenhouseMapper(), LeverMapper(), AshbyMapper()):
        register_mapper(mapper)