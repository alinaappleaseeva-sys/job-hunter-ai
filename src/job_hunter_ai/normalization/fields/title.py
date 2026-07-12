"""Title normalization helpers."""

from __future__ import annotations

import re

_WHITESPACE = re.compile(r"\s+")


def normalize_title(raw: str | None) -> tuple[str | None, str | None]:
    """Return ``(title_raw, title_normalized)``.

    ``title_raw`` is trimmed source text; ``title_normalized`` is lowercased
    for dedup/ranking comparisons.
    """
    if raw is None:
        return None, None
    cleaned = _WHITESPACE.sub(" ", raw).strip()
    if not cleaned:
        return None, None
    return cleaned, cleaned.lower()