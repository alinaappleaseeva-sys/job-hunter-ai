# Evals

`evals/` exists to keep the repository honest.

The main failure mode for this product is not "the code crashes". The real failure mode is "the system appears to work while quietly accumulating junk data, duplicates, irrelevant jobs, and fake openings".

Because of that, every major subsystem should have both:
- deterministic tests in `tests/`
- data-backed evaluation suites in `evals/`

## Evaluation Families

### 1. Ingestion Quality
Questions:
- Did the connector fetch the right pages or messages?
- Did it miss obvious postings?
- Did source-specific parsing regress?

### 2. Normalization Quality
Questions:
- Are title, location, company, salary, remote mode, and posted date extracted correctly?
- Are we collapsing information or hallucinating fields?

### 3. Dedup Quality
Questions:
- Are cross-posted openings merged when they should be?
- Are distinct openings incorrectly collapsed?

### 4. Ranking Quality
Questions:
- Do top-ranked jobs actually match the candidate profile?
- Is junk entering the top of the inbox?

### 5. Ghost Detection Quality
Questions:
- Are obvious stale or evergreen jobs being downranked?
- Are good active jobs being falsely hidden?

## Directory Conventions

- `datasets/`: frozen or versioned examples.
- `rubrics/`: grading criteria and labels.
- `suites/`: executable suite definitions by subsystem.
- `harness/`: code to run evaluation pipelines.
- `reports/`: generated outputs, summaries, and comparisons.

## Rules For Shipping Changes

1. New connector: add or extend an ingestion eval dataset.
2. New normalizer logic: add field-level accuracy examples.
3. Dedup changes: run merge and split regression suites.
4. Ranking changes: compare top-k precision against baseline.
5. Ghost detection changes: compare precision/recall tradeoffs.

If a change improves coverage but worsens junk rate, that is not a silent win.

