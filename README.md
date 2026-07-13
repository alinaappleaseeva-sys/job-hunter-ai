# Job Hunter AI

Starter repository for an AI service that finds, normalizes, ranks, and filters job opportunities from multiple sources.

The product direction for this repository is:
- ingest jobs from ATS, job boards, company sites, and Telegram channels;
- normalize all postings into one canonical schema;
- deduplicate mirrored openings across sources;
- rank jobs against a personal candidate profile;
- downrank or hide likely ghost jobs;
- evaluate every important step so we do not silently scale junk.

## Repository Principles

1. `evals` are part of the product, not a side task.
2. No connector is considered healthy only because it returns data.
3. No ranking change is accepted only because it feels better in ad hoc inspection.
4. Every stage must have explicit quality checks before we increase source coverage.

## Current Focus (July 2026)

We continue to follow the Repository Principles above without exception.

Current active work shifts the emphasis toward making the system useful for a **real senior candidate profile**:

- Target: Head of Operations, Chief of Staff, Program Management roles in **blockchain/web3/crypto** and adjacent domains (fintech, security, AI-web3 hybrids).
- Goals for this stage: significantly increase recall of relevant senior/head openings (target: hundreds visible), improve role-fit signals for high-priority titles, handle salary information honestly (no fabrication of thresholds, 120k+ is acceptable), and expand the sources that actually feed the ranking.
- Strong emphasis on **explicit per-phase success metrics**, automated checks, configurable components, robust source fetching (rate limits, concurrency, error recovery), and automation/observability suitable for repeated Hermes-driven runs.
- We are operating from the detailed plan: `docs/plans/implementation-plan-job-aggregator-ranking.md`.

All changes still go through measurable quality gates before increasing coverage or changing ranking behavior.

## Initial Layout

- `docs/`: PRD, architecture, specs, decisions, research notes, and implementation plans.
- `src/job_hunter_ai/`: application code.
- `tests/`: unit and integration tests for deterministic behavior.
- `evals/`: datasets, rubrics, suites, harness, and reports.
- `ops/`: runbooks, jobs, and operational policies.
- `scripts/`: repository automation and local developer utilities (including autonomous cycles).

## Evaluation-First Development

The repository is intentionally organized so evaluation sits next to implementation.

We expect at least five evaluation families:
- source ingestion quality
- normalization accuracy
- dedup quality
- personal ranking quality
- ghost-job detection quality

Before adding new sources or shipping model changes, we should be able to answer:
- Did coverage increase?
- Did junk increase?
- Did ranking precision drop?
- Did ghost false positives increase?

See [evals/README.md](./evals/README.md) for the operating model.

## Suggested Build Order

1. Define canonical schemas and source contracts.
2. Implement one or two ATS connectors.
3. Build normalization and dedup baselines.
4. Create small gold datasets in `evals/datasets/`.
5. Add ranking and ghost detection only with measurable gates.

## Active Plans & Automation

See `docs/plans/` for the current stage plans (e.g. `implementation-plan-job-aggregator-ranking.md`).

Current focus includes building toward autonomous operation:
- `scripts/autonomous_cycle.py` (planned) for repeatable pipeline runs with telemetry.
- Per-phase success metrics and automated checks.
- CI gates that run evals + HTML report generation.

## Next Documents To Add

- PRD in `docs/prd/`
- architecture decision records in `docs/decisions/`
- source contract spec in `docs/specs/`
- dataset definitions in `evals/datasets/`
- acceptance rubrics in `evals/rubrics/`
- `.github/workflows/` for tests + eval + report generation
