# Storage Model

This document defines the storage model for the MVP of Job Hunter AI.

It translates the earlier specs into persistent entities. The goal is not only to store jobs, but to store enough evidence to support normalization, dedup, ranking, ghost detection, and evaluation.

The storage model must support five needs simultaneously:

1. preserve raw source truth;
2. persist normalized postings;
3. persist canonical jobs and merge history;
4. persist candidate-facing ranking and ghost decisions;
5. persist eval and operational evidence.

## 1. Design Principles

1. Raw records are first-class evidence.
2. Normalized postings and canonical jobs are different persistence layers.
3. We store enough lineage to debug source, parse, and dedup mistakes.
4. We optimize for reviewability over premature compression.
5. Storage must make evals easy to run, not harder.

## 2. Storage Layers

The MVP should store data in six conceptual layers:

1. source definitions and connector state
2. raw records
3. normalized postings
4. canonical jobs and merge events
5. candidate profile and match outputs
6. feedback and eval artifacts

## 3. Recommended Primary Database

Use PostgreSQL for the MVP.

Why:
- relational joins are important for lineage and dedup auditability;
- JSONB is useful for raw payloads and connector metadata;
- text search and trigram support are helpful for dedup and debugging;
- transaction safety matters for cursor updates and merge operations.

Supplementary components can come later:
- Redis for queues and transient job state
- object storage if fixture or raw payload volume grows materially

## 4. Core Tables

## 4.1 `sources`

Stores source definitions and rollout metadata.

### Purpose
- track the source inventory that became implementation scope;
- distinguish source family and provider;
- store rollout and maintenance metadata.

### Fields
- `source_id` UUID PK
- `source_name` TEXT UNIQUE NOT NULL
- `source_type` TEXT NOT NULL
- `provider` TEXT NULL
- `base_url` TEXT NULL
- `status` TEXT NOT NULL
- `priority_tier` TEXT NULL
- `auth_requirements` JSONB NOT NULL DEFAULT '{}'::jsonb
- `rate_limit_notes` TEXT NULL
- `rollout_notes` TEXT NULL
- `created_at` TIMESTAMP NOT NULL
- `updated_at` TIMESTAMP NOT NULL

### Suggested status values
- `candidate`
- `enabled`
- `paused`
- `research_needed`
- `rejected`

## 4.2 `source_cursors`

Stores connector progress for resumable fetching.

### Purpose
- incremental source fetch
- cursor resume after partial failure
- operational inspection of source progress

### Fields
- `cursor_id` UUID PK
- `source_id` UUID NOT NULL FK -> `sources.source_id`
- `cursor_type` TEXT NOT NULL
- `cursor_value` TEXT NULL
- `last_success_at` TIMESTAMP NULL
- `last_error_at` TIMESTAMP NULL
- `last_error_type` TEXT NULL
- `last_error_message` TEXT NULL
- `updated_at` TIMESTAMP NOT NULL

### Notes
- one source can later have multiple cursors if we segment by channel or partition

## 4.3 `source_runs`

Stores one execution summary per connector run.

### Purpose
- source telemetry
- operational debugging
- source quality and reliability review

### Fields
- `source_run_id` UUID PK
- `source_id` UUID NOT NULL FK -> `sources.source_id`
- `started_at` TIMESTAMP NOT NULL
- `finished_at` TIMESTAMP NULL
- `success` BOOLEAN NOT NULL
- `records_fetched` INTEGER NOT NULL DEFAULT 0
- `records_emitted` INTEGER NOT NULL DEFAULT 0
- `records_persisted` INTEGER NOT NULL DEFAULT 0
- `cursor_before` TEXT NULL
- `cursor_after` TEXT NULL
- `error_type` TEXT NULL
- `error_message` TEXT NULL
- `run_metadata` JSONB NOT NULL DEFAULT '{}'::jsonb

### Why it matters
- this table feeds connector health review and source eval summaries

## 4.4 `raw_source_records`

Stores the untouched or minimally wrapped source record.

### Purpose
- preserve source evidence
- support replay and debugging
- support fixture extraction and eval refresh

### Fields
- `raw_record_id` UUID PK
- `source_id` UUID NOT NULL FK -> `sources.source_id`
- `source_run_id` UUID NULL FK -> `source_runs.source_run_id`
- `record_type` TEXT NOT NULL
- `external_id` TEXT NULL
- `source_url` TEXT NULL
- `fetched_at` TIMESTAMP NOT NULL
- `discovered_at` TIMESTAMP NULL
- `content_hash` TEXT NULL
- `cursor_value` TEXT NULL
- `payload` JSONB NOT NULL
- `metadata` JSONB NOT NULL DEFAULT '{}'::jsonb
- `created_at` TIMESTAMP NOT NULL

### Suggested indexes
- `(source_id, fetched_at DESC)`
- `(source_id, external_id)`
- `(content_hash)`

## 4.5 `normalized_job_postings`

Stores one normalized posting per source-specific job artifact.

### Purpose
- provide the shared shape for downstream dedup and ranking
- preserve source-specific normalized fields and parse diagnostics

### Fields
- `posting_id` UUID PK
- `raw_record_id` UUID NOT NULL FK -> `raw_source_records.raw_record_id`
- `source_id` UUID NOT NULL FK -> `sources.source_id`
- `external_id` TEXT NULL
- `source_url` TEXT NULL
- `company_name` TEXT NULL
- `company_domain` TEXT NULL
- `title_raw` TEXT NULL
- `title_normalized` TEXT NULL
- `description_raw` TEXT NULL
- `description_text` TEXT NULL
- `location_raw` TEXT NULL
- `location_country` TEXT NULL
- `location_region` TEXT NULL
- `location_city` TEXT NULL
- `remote_mode` TEXT NULL
- `employment_type` TEXT NULL
- `seniority` TEXT NULL
- `role_family` TEXT NULL
- `market` TEXT NULL
- `compensation_min` NUMERIC NULL
- `compensation_max` NUMERIC NULL
- `compensation_currency` TEXT NULL
- `posted_at` TIMESTAMP NULL
- `discovered_at` TIMESTAMP NULL
- `normalized_at` TIMESTAMP NOT NULL
- `content_hash` TEXT NULL
- `parse_status` TEXT NOT NULL
- `parse_warnings` JSONB NOT NULL DEFAULT '[]'::jsonb

### Suggested parse status values
- `parsed`
- `partial`
- `failed`

### Suggested indexes
- `(company_domain)`
- `(title_normalized)`
- `(posted_at)`
- trigram or text-search support on `description_text`

## 4.6 `canonical_jobs`

Stores one logical opening after dedup.

### Purpose
- consolidate duplicates
- serve ranking and candidate-facing product logic
- store canonical-level ghost and freshness signals

### Fields
- `canonical_job_id` UUID PK
- `primary_posting_id` UUID NOT NULL FK -> `normalized_job_postings.posting_id`
- `company_name` TEXT NULL
- `company_domain` TEXT NULL
- `title_normalized` TEXT NULL
- `role_family` TEXT NULL
- `seniority` TEXT NULL
- `market` TEXT NULL
- `remote_mode` TEXT NULL
- `employment_type` TEXT NULL
- `location_country` TEXT NULL
- `location_region` TEXT NULL
- `location_city` TEXT NULL
- `compensation_min` NUMERIC NULL
- `compensation_max` NUMERIC NULL
- `compensation_currency` TEXT NULL
- `canonical_posted_at` TIMESTAMP NULL
- `first_seen_at` TIMESTAMP NOT NULL
- `last_seen_at` TIMESTAMP NOT NULL
- `active_posting_count` INTEGER NOT NULL DEFAULT 1
- `source_count` INTEGER NOT NULL DEFAULT 1
- `ghost_score` NUMERIC NULL
- `canonical_status` TEXT NOT NULL
- `merge_confidence` NUMERIC NULL
- `merge_reasons` JSONB NOT NULL DEFAULT '[]'::jsonb
- `created_at` TIMESTAMP NOT NULL
- `updated_at` TIMESTAMP NOT NULL

### Suggested canonical status values
- `active`
- `stale`
- `closed`
- `uncertain`

## 4.7 `canonical_job_postings`

Join table linking postings to canonical jobs.

### Purpose
- one canonical job contains many postings
- one posting belongs to one canonical job in MVP

### Fields
- `canonical_job_id` UUID NOT NULL FK -> `canonical_jobs.canonical_job_id`
- `posting_id` UUID NOT NULL FK -> `normalized_job_postings.posting_id`
- `linked_at` TIMESTAMP NOT NULL
- `link_status` TEXT NOT NULL DEFAULT 'active'
- PRIMARY KEY (`canonical_job_id`, `posting_id`)

### Why separate join table
- easier audit and re-linking
- future-proofing for merge review and overrides

## 4.8 `canonical_merge_events`

Stores dedup explanations and manual overrides.

### Purpose
- auditability of merge decisions
- postmortem debugging of false merges and missed merges

### Fields
- `merge_event_id` UUID PK
- `canonical_job_id` UUID NOT NULL FK -> `canonical_jobs.canonical_job_id`
- `posting_id` UUID NOT NULL FK -> `normalized_job_postings.posting_id`
- `merged_at` TIMESTAMP NOT NULL
- `merge_confidence` NUMERIC NULL
- `merge_reasons` JSONB NOT NULL DEFAULT '[]'::jsonb
- `reviewer_override` BOOLEAN NOT NULL DEFAULT FALSE
- `review_notes` TEXT NULL

## 4.9 `candidate_profiles`

Stores candidate preferences used by ranking.

### Purpose
- personalize ranking
- make ranking configurable without hardcoding user logic

### Fields
- `candidate_profile_id` UUID PK
- `profile_name` TEXT NOT NULL
- `target_roles` JSONB NOT NULL DEFAULT '[]'::jsonb
- `target_markets` JSONB NOT NULL DEFAULT '[]'::jsonb
- `target_seniority` JSONB NOT NULL DEFAULT '[]'::jsonb
- `preferred_locations` JSONB NOT NULL DEFAULT '[]'::jsonb
- `remote_preferences` JSONB NOT NULL DEFAULT '[]'::jsonb
- `salary_floor` NUMERIC NULL
- `must_have` JSONB NOT NULL DEFAULT '[]'::jsonb
- `must_not_have` JSONB NOT NULL DEFAULT '[]'::jsonb
- `preferred_company_traits` JSONB NOT NULL DEFAULT '[]'::jsonb
- `created_at` TIMESTAMP NOT NULL
- `updated_at` TIMESTAMP NOT NULL

## 4.10 `job_matches`

Stores ranking outputs for a candidate profile against canonical jobs.

### Purpose
- persist ranking decisions
- support candidate feed, review, and eval comparisons

### Fields
- `job_match_id` UUID PK
- `candidate_profile_id` UUID NOT NULL FK -> `candidate_profiles.candidate_profile_id`
- `canonical_job_id` UUID NOT NULL FK -> `canonical_jobs.canonical_job_id`
- `match_score` NUMERIC NOT NULL
- `role_fit_score` NUMERIC NULL
- `market_fit_score` NUMERIC NULL
- `seniority_fit_score` NUMERIC NULL
- `salary_fit_score` NUMERIC NULL
- `location_fit_score` NUMERIC NULL
- `quality_fit_score` NUMERIC NULL
- `ghost_penalty_score` NUMERIC NULL
- `decision` TEXT NOT NULL
- `review_state` TEXT NOT NULL DEFAULT 'new'
- `explanation` JSONB NOT NULL DEFAULT '{}'::jsonb
- `scored_at` TIMESTAMP NOT NULL

### Suggested decision values
- `show`
- `downrank`
- `hide`

### Suggested review state values
- `new`
- `seen`
- `saved`
- `dismissed`
- `applied`

## 4.11 `feedback_events`

Stores user feedback on matches and jobs.

### Purpose
- future ranking improvements
- ghost and dedup debugging
- product insight into false positives and false negatives

### Fields
- `feedback_event_id` UUID PK
- `candidate_profile_id` UUID NULL FK -> `candidate_profiles.candidate_profile_id`
- `canonical_job_id` UUID NULL FK -> `canonical_jobs.canonical_job_id`
- `posting_id` UUID NULL FK -> `normalized_job_postings.posting_id`
- `job_match_id` UUID NULL FK -> `job_matches.job_match_id`
- `feedback_type` TEXT NOT NULL
- `feedback_payload` JSONB NOT NULL DEFAULT '{}'::jsonb
- `created_at` TIMESTAMP NOT NULL

### Suggested feedback types
- `relevant`
- `not_relevant`
- `duplicate`
- `ghost_likely`
- `applied`
- `wrong_seniority`
- `wrong_market`

## 4.12 `eval_runs`

Stores structured evaluation executions.

### Purpose
- compare connector or ranking changes across revisions
- keep eval outputs queryable

### Fields
- `eval_run_id` UUID PK
- `eval_suite_name` TEXT NOT NULL
- `git_ref` TEXT NULL
- `started_at` TIMESTAMP NOT NULL
- `finished_at` TIMESTAMP NULL
- `success` BOOLEAN NOT NULL
- `summary_metrics` JSONB NOT NULL DEFAULT '{}'::jsonb
- `report_path` TEXT NULL
- `notes` TEXT NULL

## 4.13 `eval_examples`

Stores labeled example outcomes when we want DB-backed traceability.

### Purpose
- link eval judgments to records or jobs
- support later regression analysis

### Fields
- `eval_example_id` UUID PK
- `eval_run_id` UUID NOT NULL FK -> `eval_runs.eval_run_id`
- `entity_type` TEXT NOT NULL
- `entity_id` UUID NULL
- `label` TEXT NOT NULL
- `prediction` TEXT NULL
- `score` NUMERIC NULL
- `details` JSONB NOT NULL DEFAULT '{}'::jsonb

## 5. Entity Relationships

High-level graph:

- one `source` has many `source_runs`
- one `source` has many `raw_source_records`
- one `raw_source_record` produces zero or one `normalized_job_postings` in MVP
- many `normalized_job_postings` can map to one `canonical_job`
- one `canonical_job` has one `primary_posting_id`
- one `candidate_profile` can have many `job_matches`
- one `job_match` points to one `canonical_job`
- many `feedback_events` can refer to the same `canonical_job` or `job_match`

## 6. Minimum Index Strategy

At MVP stage we should add indexes for the most common operations.

### Source and raw record access
- `raw_source_records(source_id, fetched_at desc)`
- `raw_source_records(source_id, external_id)`

### Posting lookup and dedup support
- `normalized_job_postings(company_domain)`
- `normalized_job_postings(title_normalized)`
- `normalized_job_postings(posted_at)`
- optional trigram index on `description_text`

### Canonical and ranking access
- `canonical_jobs(company_domain, title_normalized)`
- `job_matches(candidate_profile_id, match_score desc)`
- `job_matches(candidate_profile_id, review_state)`

## 7. Retention Guidance

### Keep long-lived
- `sources`
- `source_cursors`
- `normalized_job_postings`
- `canonical_jobs`
- `canonical_merge_events`
- `candidate_profiles`
- `job_matches`
- `feedback_events`
- `eval_runs`

### Retain with review policy
- `raw_source_records`

We should retain raw records as long as practical because they are essential evidence for:
- source debugging
- parser drift diagnosis
- fixture extraction
- eval refresh

If storage becomes a concern, move old payloads to colder storage, not silent deletion.

## 8. How The Model Supports Evals

### Ingestion evals
- use `source_runs`
- use `raw_source_records`

### Normalization evals
- compare `normalized_job_postings` against gold labels

### Dedup evals
- inspect `canonical_job_postings` and `canonical_merge_events`

### Ranking evals
- inspect `job_matches`

### Ghosting evals
- inspect `canonical_jobs.ghost_score`
- inspect posting history in `normalized_job_postings`

## 9. MVP Simplifications

To keep implementation focused, the MVP may simplify these areas:

1. No full field-level provenance table yet.
2. No temporal versioning of every posting field yet.
3. No multi-tenant profile system yet.
4. No complex workflow state machine yet.
5. No object-storage offload yet unless raw payload volume forces it.

These are deliberate postponements, not omissions by accident.

## 10. Acceptance Criteria For Storage Model

The storage model is good enough for MVP implementation when:

1. every source can persist raw records and run summaries;
2. normalization has a stable destination table;
3. dedup can cluster postings into canonical jobs;
4. ranking can target canonical jobs and persist explanations;
5. ghost scoring can store canonical and posting-level signals;
6. eval results can be persisted and compared over time.

## 11. Relationship To Other Specs

This document depends on:
- `docs/specs/source-contract.md`
- `docs/specs/canonical-job-schema.md`

This document should inform:
- migration design
- ORM or data-access layer design
- dedup implementation details
- ranking and ghosting persistence rules

