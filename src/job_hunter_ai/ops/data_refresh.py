"""Data refresh and dataset curation (Phase 10 skeleton)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def should_refresh_dataset(
    last_refresh: datetime | None,
    max_age_hours: int = 72,
    force: bool = False,
) -> bool:
    if force:
        return True
    if last_refresh is None:
        return True
    age = (datetime.utcnow() - last_refresh).total_seconds() / 3600
    return age > max_age_hours


def curate_freshness_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Very lightweight freshness report."""
    now = datetime.utcnow()
    ages = []
    for r in records:
        ts = r.get("discovered_at") or r.get("fetched_at")
        if ts:
            try:
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                ages.append((now - ts).total_seconds() / 3600)
            except Exception:
                pass
    if not ages:
        return {"median_age_hours": None, "stale_48h_ratio": 0.0}
    ages.sort()
    median = ages[len(ages)//2]
    stale = sum(1 for a in ages if a > 48) / len(ages)
    return {
        "median_age_hours": round(median, 1),
        "stale_48h_ratio": round(stale, 3),
        "recommendation": "refresh" if stale > 0.3 or median > 36 else "ok",
    }
