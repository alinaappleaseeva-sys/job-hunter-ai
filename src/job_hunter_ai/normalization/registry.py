"""Mapper registry — routes ``source_name`` to provider-specific normalizers."""

from __future__ import annotations

from job_hunter_ai.normalization.mappers.base import BaseMapper

_MAPPERS: dict[str, BaseMapper] = {}


def resolve_provider(source_name: str) -> str:
    """Extract provider slug from ``source_name`` (e.g. ``greenhouse:stripe`` → ``greenhouse``)."""
    if ":" in source_name:
        return source_name.split(":", 1)[0].strip().lower()
    return source_name.strip().lower()


def get_mapper(source_name: str) -> BaseMapper | None:
    """Return the registered mapper for a source, if any."""
    return _MAPPERS.get(resolve_provider(source_name))


def register_mapper(mapper: BaseMapper) -> None:
    """Register a provider mapper (used by ATS mapper modules in Step 4.4)."""
    _MAPPERS[mapper.provider] = mapper


def registered_providers() -> frozenset[str]:
    """Return providers with a registered mapper — test/diagnostic helper."""
    return frozenset(_MAPPERS)