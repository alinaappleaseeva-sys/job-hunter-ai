# Telegram Noise / Quality Rubric (Phase 10)

## Goals
- Measure how much of Telegram ingestion is actual job signal vs noise/duplicate/stale
- Prevent noise explosion when moving from stub to real client

## Fields
- is_job: contains clear hiring signal
- is_unique: not duplicate of recent canonical
- freshness_hours: hours since posted

## Target thresholds (for production channels)
- job_signal_rate ≥ 0.60
- unique_job_rate ≥ 0.70
- median_freshness_hours ≤ 24

## Examples
good_signal: clear job + unique + fresh
duplicate_stale: valid job but already seen or old
noise: no hiring intent