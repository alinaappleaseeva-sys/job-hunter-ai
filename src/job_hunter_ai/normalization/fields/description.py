"""Description extraction helpers."""

from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def html_to_text(value: str | None) -> str | None:
    """Best-effort HTML → plain text without external dependencies."""
    if not value or not str(value).strip():
        return None
    unescaped = html.unescape(value)
    text = _TAG_RE.sub(" ", unescaped)
    text = _WS_RE.sub(" ", text).strip()
    return text or None


def pick_description(
    *candidates: str | None,
    prefer_plain: bool = True,
) -> tuple[str | None, str | None]:
    """Choose description fields from provider-specific candidates.

    Returns ``(description_raw, description_text)``. When a candidate looks
    like HTML it is stored as raw and converted to text; plain strings populate
    both fields.
    """
    ordered = [c for c in candidates if c and str(c).strip()]
    if not ordered:
        return None, None

    chosen = ordered[0]
    if "<" in chosen and ">" in chosen:
        return chosen, html_to_text(chosen)

    if prefer_plain and len(ordered) > 1:
        plain = ordered[1]
        if plain and "<" not in plain:
            return ordered[0], plain

    return chosen, chosen