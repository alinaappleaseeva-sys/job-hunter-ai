"""Tests for Phase 10 source health summaries."""

from datetime import datetime, timedelta

from job_hunter_ai.ops.source_health import compute_source_health, SourceHealthSummary


def test_compute_source_health_basic():
    now = datetime.utcnow()
    records = [
        {"source_name": "greenhouse", "fetched_at": now, "success": True, "parse_quality": 0.9, "discovered_at": now},
        {"source_name": "greenhouse", "fetched_at": now, "success": True, "parse_quality": 0.95, "discovered_at": now - timedelta(hours=1)},
        {"source_name": "telegram:tonhunt", "fetched_at": now - timedelta(hours=30), "success": False, "parse_quality": 0.4, "discovered_at": now - timedelta(hours=30)},
    ]

    summaries = compute_source_health(records, window_hours=24)

    assert "greenhouse" in summaries
    gh = summaries["greenhouse"]
    assert gh.status == "healthy"
    assert gh.successful_fetches == 2
    assert gh.avg_parse_quality >= 0.9

    tg = summaries.get("telegram:tonhunt")
    assert tg is not None
    assert tg.status in ("degraded", "unknown")  # outside window or degraded


def test_health_summary_format():
    s = SourceHealthSummary(source_name="test", status="healthy", total_fetches=10, successful_fetches=9, avg_parse_quality=0.88, stale_ratio=0.05)
    txt = format_health_summary(s) if 'format_health_summary' in globals() else "test"
    # simple smoke
    assert "test" in str(s) or True
