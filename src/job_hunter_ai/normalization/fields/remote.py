"""Remote / hybrid / onsite mode normalization."""

from __future__ import annotations

_ALLOWED = frozenset({"remote", "hybrid", "onsite", "unknown"})


def normalize_remote_mode(
    *,
    workplace_type: str | None = None,
    is_remote: bool | None = None,
    location_raw: str | None = None,
    categories_remote: str | bool | None = None,
) -> str:
    """Infer canonical ``remote_mode`` from provider signals."""
    wt = (workplace_type or "").strip().lower().replace("_", "-")
    if wt == "remote":
        return "remote"
    if wt == "hybrid":
        return "hybrid"
    if wt in {"onsite", "on-site"}:
        return "onsite"

    if categories_remote is True or (
        isinstance(categories_remote, str) and categories_remote.strip().lower() == "remote"
    ):
        return "remote"

    if is_remote is True:
        return "remote"
    if is_remote is False:
        return "onsite"

    if wt == "unspecified":
        return "unknown"

    loc_signal = _remote_signal_from_location(location_raw)
    if loc_signal:
        return loc_signal

    if location_raw and str(location_raw).strip():
        return "onsite"

    return "unknown"


def _remote_signal_from_location(location_raw: str | None) -> str | None:
    if not location_raw:
        return None
    lower = location_raw.lower()
    if "hybrid" in lower:
        return "hybrid"
    if "remote" not in lower:
        return None
    if ";" in location_raw:
        return "hybrid"
    if "us-west remote" in lower and "," in location_raw:
        return "hybrid"
    return "remote"