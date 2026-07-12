"""Employment type normalization."""

from __future__ import annotations

_EMPLOYMENT_MAP: dict[str, str] = {
    "fulltime": "full-time",
    "full-time": "full-time",
    "full time": "full-time",
    "regular full time (salary)": "full-time",
    "parttime": "part-time",
    "part-time": "part-time",
    "part time": "part-time",
    "contract": "contract",
    "contractor": "contract",
    "intern": "internship",
    "internship": "internship",
    "temporary": "contract",
}


def normalize_employment_type(raw: str | None) -> str | None:
    """Map provider employment strings to canonical values."""
    if not raw or not str(raw).strip():
        return None
    key = str(raw).strip().lower()
    if key in _EMPLOYMENT_MAP:
        return _EMPLOYMENT_MAP[key]
    compact = "".join(ch for ch in key if ch.isalnum())
    if compact in _EMPLOYMENT_MAP:
        return _EMPLOYMENT_MAP[compact]
    return key if key in {"full-time", "part-time", "contract", "internship"} else None