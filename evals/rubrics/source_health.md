# Source Health Rubric (Phase 10)

## Purpose
Detect when a source degrades (fetch failures, low parse quality, high staleness) before it pollutes the delivery pipeline.

## Metrics
- success_rate: successful fetches / attempts in window
- avg_parse_quality: average field coverage / validity score
- stale_ratio: portion of records older than freshness threshold

## Labels
- healthy: success_rate ≥ 0.90, avg_parse_quality ≥ 0.80, stale_ratio ≤ 0.15
- degraded_fetch: success_rate < 0.80
- low_quality_parse: avg_parse_quality < 0.70
- high_staleness: stale_ratio > 0.25

## Gates
- Alert on any source dropping below healthy thresholds for >1 window
- Require triage action before re-enabling a degraded source