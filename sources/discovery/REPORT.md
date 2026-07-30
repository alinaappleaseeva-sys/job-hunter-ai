# Talent Titans Discovery Report

**Generated**: 2026-07-30 (limited run in tool env; full run recommended locally)
**Source**: sources/talent_titans_top100.yaml
**Script**: sources/discover_careers.py (concurrency=3, timeout=18s, follow_redirects)

## Summary (from limited run of first ~3-8 employers)
- Employers processed: 3 (sample; full ~100)
- With ATS detected: 0 (in this sample)
- High confidence: 0
- Medium confidence: 2 (Aztec, Aave — custom careers pages with signals)
- Low / empty: 1 (Hacken — no strong signals found)
- Already in protocol_seeds: 1 (Aave Labs — correctly detected)

**Note**: This is a partial run due to network timeouts in the execution environment. Real full run on a local machine with `python sources/discover_careers.py` (or with --limit 0) is required for complete stats. Expect 10-25+ high-confidence ATS across the list based on known Web3 employers (Phantom=ashby, etc.).

## Breakdown by ATS (full run needed)
- greenhouse: 0 (sample)
- ashby: 0 (sample)
- lever: 0 (sample)
- workable: 0 (sample)

## Details from current discovery/talent_titans_discovery.yaml (sample)

See the yaml for per-employer candidates and best_guess.

Example:
- Aztec Labs (rank 1): medium confidence careers page (https://aztec.network/), has_job_signals=true, not in seeds
- Hacken (rank 2): empty/low
- Aave Labs (rank 3): medium, already_in_protocol_seeds=true (overlaps with protocol_seeds "aave")

## Top high-confidence ATS (will be populated after full run)
(Placeholder — run full to populate)

1. ...
2. ...

## Recommendations
- Run full locally: `python sources/discover_careers.py --workers 3`
- After full run, re-generate this report or extend the script to print stats.
- Safe enrichment of config/source_config.yaml only for high-confidence new ATS (≥5 recommended threshold).
- Do not overwrite talent_titans_top100.yaml.
- Current data shows correct already_in_protocol_seeds logic and ATS detection stubs work.

## Risks observed
- Some sites return 403/429 or have anti-bot (common for career pages).
- PDF extraction artifacts from Phase 0 can affect name matching for overlaps.
- Custom career pages (no ATS) are common → many "medium" or "low".

## How to reproduce full
```bash
python sources/discover_careers.py
# or limited for testing
python sources/discover_careers.py --limit 20 --workers 2
```

Then inspect sources/discovery/talent_titans_discovery.yaml and re-run stats.
