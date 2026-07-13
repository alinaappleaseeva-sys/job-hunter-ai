"""Source health monitoring (Phase 10).

Basic summaries for detecting degraded sources.
Used for dashboards and triage.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class SourceHealthSummary:
    source_name: str
    window_hours: int = 24
    total_fetches: int = 0
    successful_fetches: int = 0
    avg_parse_quality: float = 0.0
    stale_ratio: float = 0.0
    last_success_at: datetime | None = None
    status: str = "unknown"  # healthy | degraded | unknown


def compute_source_health(
    records: list[dict[str, Any]],
    window_hours: int = 24,
) -> dict[str, SourceHealthSummary]:
    """Compute basic health summaries per source from raw or normalized records.

    Expects records to have at least:
      - source_name
      - fetched_at (or timestamp)
      - parse_quality (optional, 0-1)
      - discovered_at or date (for staleness)
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=window_hours)

    by_source: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        src = r.get("source_name") or r.get("source")
        if src:
            by_source[src].append(r)

    summaries: dict[str, SourceHealthSummary] = {}

    for source, recs in by_source.items():
        window_recs = []
        for r in recs:
            ts = r.get("fetched_at") or r.get("timestamp")
            if ts:
                try:
                    if isinstance(ts, str):
                        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if ts >= cutoff:
                        window_recs.append(r)
                except Exception:
                    continue

        total = len(window_recs)
        if total == 0:
            summaries[source] = SourceHealthSummary(source_name=source, window_hours=window_hours, status="unknown")
            continue

        successes = sum(1 for r in window_recs if r.get("success", True))
        qualities = [r.get("parse_quality", 0.8) for r in window_recs if "parse_quality" in r]
        avg_q = sum(qualities) / len(qualities) if qualities else 0.75

        stale = 0
        for r in window_recs:
            d = r.get("discovered_at") or r.get("date")
            if d:
                try:
                    if isinstance(d, str):
                        d = datetime.fromisoformat(d.replace("Z", "+00:00"))
                    if (now - d).total_seconds() > window_hours * 3600 * 0.5:
                        stale += 1
                except Exception:
                    pass

        stale_ratio = stale / total if total else 0.0
        success_rate = successes / total

        if success_rate < 0.8 or avg_q < 0.7 or stale_ratio > 0.25:
            status = "degraded"
        else:
            status = "healthy"

        summaries[source] = SourceHealthSummary(
            source_name=source,
            window_hours=window_hours,
            total_fetches=total,
            successful_fetches=successes,
            avg_parse_quality=round(avg_q, 3),
            stale_ratio=round(stale_ratio, 3),
            last_success_at=now,
            status=status,
        )

    return summaries


def format_health_summary(summary: SourceHealthSummary) -> str:
    return (
        f"{summary.source_name}: {summary.status} "
        f"(success={summary.successful_fetches}/{summary.total_fetches}, "
        f"parse={summary.avg_parse_quality}, stale={summary.stale_ratio})"
    )
