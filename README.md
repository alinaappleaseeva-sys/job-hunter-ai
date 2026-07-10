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

## Initial Layout

- `docs/`: PRD, architecture, specs, decisions, and research notes.
- `src/job_hunter_ai/`: application code.
- `tests/`: unit and integration tests for deterministic behavior.
- `evals/`: datasets, rubrics, suites, harness, and reports.
- `ops/`: runbooks, jobs, and operational policies.
- `scripts/`: repository automation and local developer utilities.

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

## Next Documents To Add

- PRD in `docs/prd/`
- architecture decision records in `docs/decisions/`
- source contract spec in `docs/specs/`
- dataset definitions in `evals/datasets/`
- acceptance rubrics in `evals/rubrics/`
