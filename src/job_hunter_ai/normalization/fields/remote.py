"""Remote / hybrid / onsite mode normalization."""

from __future__ import annotations

_ALLOWED = frozenset({"remote", "hybrid", "onsite", "unknown"})


def normalize_remote_mode(
    *,
    workplace_type: str | None = None,
    is_remote: bool | None = None,
    location_raw: str | None = None,
    categories_remote: str | bool | None = None,
    description: str | None = None,
) -> str:
    """Infer canonical ``remote_mode`` from provider signals.

    Enhanced to also scan description text for remote/hybrid/onsite signals
    when other signals are weak.
    """
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

    desc_signal = _remote_signal_from_description(description)
    if desc_signal:
        return desc_signal

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


def _remote_signal_from_description(desc: str | None) -> str | None:
    """Extract remote/hybrid/onsite signal from job description text.

    Looks for strong explicit signals first.
    """
    if not desc:
        return None

    lower = desc.lower()

    # Strong explicit signals
    strong_remote = [
        "fully remote", "100% remote", "completely remote",
        "remote only", "work from anywhere", "wfa", "remote-first"
    ]
    if any(phrase in lower for phrase in strong_remote):
        return "remote"

    if "hybrid" in lower or "flexible location" in lower or "remote/hybrid" in lower:
        return "hybrid"

    strong_onsite = [
        "on-site", "onsite", "in-office", "in office", "office-based",
        "must be in", "located in our office", "work from office"
    ]
    if any(phrase in lower for phrase in strong_onsite):
        return "onsite"

    # Weaker but useful signals
    if "remote" in lower and ("work from home" in lower or "wfh" in lower):
        return "remote"

    # If "remote" appears prominently and no strong onsite signal, lean remote
    remote_mentions = lower.count("remote")
    if remote_mentions >= 2 and "onsite" not in lower and "on-site" not in lower:
        return "remote"

    return None
