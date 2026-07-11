# Implementation Plan

This document is the execution plan for building the MVP of Job Hunter AI.

It is intentionally written as a delivery plan, not just a wishlist. Each phase should end with a concrete artifact, a review checkpoint, and explicit evaluation gates so we do not scale low-quality ingestion, noisy ranking, or broken ghost-job logic.

## 1. Goals Of The MVP

The MVP should prove four things:

1. We can ingest jobs from multiple source families into one normalized store.
2. We can merge duplicate postings into canonical jobs without obvious collapse errors.
3. We can rank jobs for one candidate profile better than naive search feeds.
4. We can suppress stale or ghost-like jobs without hiding too many good opportunities.

## 2. Delivery Principles

1. Build the data pipeline before the “agent magic”.
2. Prefer explainable heuristics before opaque model-driven scoring.
3. Add source coverage only when evals show that junk is still under control.
4. Keep pull requests short, reviewable, and measurable.
5. Every subsystem needs both implementation tests and data-backed evals.

## 3. Target MVP Scope

### In scope

- ATS connectors and easier boards prioritized by effort-to-value, not by surface popularity
- first-wave sources: Greenhouse, Lever, Wellfound, Remote OK, Solana Jobs, selected Telegram channels
- second-wave sources: Ashby, Habr Career
- later or research-heavy sources: hh.ru, LinkedIn and other sources with meaningful anti-bot or third-party access constraints
- Telegram: a small first batch of channels
- Canonical job schema
- Posting-to-canonical dedup
- One candidate profile
- Initial ranking logic
- Initial ghost-job scoring logic
- Digest or inbox-style delivery

### Out of scope for the first MVP

- universal browser automation for every source
- multi-profile team features
- auto-apply workflows
- autonomous agent generation frameworks
- advanced self-improving orchestration
- full company crawling across the open web
- hard-access sources that require disproportionate anti-bot, heavy proxying, or expensive third-party enrichment before we validate easier coverage

## 3.1 Source Reality And Prioritization

Not all sources are equal.

For the MVP we should explicitly prioritize by `expected value / integration effort`, not by brand recognition.

### Source constraints we already know

- `hh.ru` is strategically important but operationally hard because anti-bot pressure can make ingestion expensive and brittle.
- `Ashby` is valuable but rate limits can make naive connector rollout misleadingly painful.
- `LinkedIn` has major access constraints and often requires third-party enrichment or infrastructure such as Proxycurl rather than a simple direct connector.

### Priority tiers

#### Tier 1: Fastest path to useful coverage
- Greenhouse
- Lever
- Wellfound
- Remote OK
- Solana Jobs
- selected Telegram channels

#### Tier 2: Important but somewhat harder or noisier
- Ashby
- Habr Career
- We Work Remotely
- Arc.dev

#### Tier 3: High-value but operationally expensive
- hh.ru
- LinkedIn
- Indeed

### Rule for rollout

Before we add a hard source, we should first confirm that the easier source set does **not** already give us enough coverage and candidate-quality signal for MVP learning.

The point is to get the first 80 percent of usable value from the easiest 20 percent of connector work.

## 4. Workstreams

The implementation should run in parallel across six workstreams.

### A. Repository and engineering foundations
- repo structure
- coding standards
- test layout
- eval layout
- CI hooks later

### B. Source ingestion
- connector contract
- source configs and cursors
- raw payload persistence
- source health telemetry

### C. Normalization and storage
- normalized posting schema
- canonical job model
- enrichment fields
- persistence model

### D. Matching and product logic
- candidate profile schema
- ranking pipeline
- ghost scoring pipeline
- delivery policy

### E. Evaluation system
- gold datasets
- rubrics
- suite runners
- regression comparison flow
- runnable quality formulas and scorecards

### F. Operations
- source failure handling
- manual review workflow
- triage for eval regressions
- source rollout policy

## 5. Phase Plan

## Phase 0: Project Foundations

### Objectives
- make the repo ready for focused iteration
- define execution discipline before connector work starts

### Deliverables
- repository scaffold
- `Implementation Plan`
- source inventory
- initial spec placeholders
- eval directory conventions

### Exit criteria
- team agrees on repo layout
- source inventory exists and is editable
- future PRs have clear landing zones

### Evals / gates
- no formal quality gate yet
- review gate: structure supports tests and evals as first-class citizens

## Phase 1: Canonical Contracts and Data Model

### Objectives
- define the core data model before touching multiple sources

### Tasks
1. Write source connector contract.
2. Write raw record schema.
3. Write normalized job posting schema.
4. Write canonical job schema.
5. Write candidate profile schema.
6. Define basic source metadata and cursor model.
7. Define storage table plan.

### Deliverables
- `docs/specs/source-contract.md`
- `docs/specs/canonical-job-schema.md`
- `docs/specs/storage-model.md`

### Exit criteria
- no ambiguity about what a connector emits
- no ambiguity about what normalization must produce
- dedup target object is explicitly defined

### Evals / gates
- create first schema-review checklist
- create first dataset templates for normalization and dedup

## Phase 2: Ingestion Framework

### Objectives
- make it possible to add source connectors without changing product logic

### Tasks
1. Implement source registry/config loading.
2. Implement source cursor persistence.
3. Implement raw fetch interface.
4. Implement raw snapshot persistence.
5. Implement source run logging and health status.
6. Implement one source smoke-run command.

### Deliverables
- connector base classes or interfaces
- source execution entrypoint
- raw source persistence
- source run telemetry

### Exit criteria
- any connector can emit raw records through one shared path
- failed runs are inspectable
- cursors can advance and resume

### Evals / gates
- `ingestion_smoke` suite template exists
- every connector must show:
  - records fetched
  - records persisted
  - source health outcome
- no connector is accepted without at least one fixture or smoke sample
- every connector should produce a runnable quality score, not only logs

## Phase 3: First ATS Connectors

### Objectives
- prove the ingestion architecture on sources with high leverage

### Tasks
1. Build Greenhouse connector.
2. Build Lever connector.
3. Build Ashby connector.
4. Save raw records for each source.
5. Add per-source fixture samples.

### Deliverables
- three live connectors
- source-specific fixture data
- source-specific parsing notes

### Exit criteria
- all three connectors fetch stable records
- no obvious schema drift in emitted raw objects

### Evals / gates
- ingestion smoke suite for each source
- manual spot-check of at least 10 records per connector
- failure gate: if a connector is too brittle or too noisy, it stays out of MVP rollout

## Phase 4: Normalization Pipeline

### Objectives
- convert raw records into one unified job posting schema

### Tasks
1. Implement normalization pipeline entrypoint.
2. Normalize company, title, description, location, remote mode, employment type.
3. Parse or map salary where available.
4. Add basic enrichment: role family, seniority, market.
5. Persist normalized postings.

### Deliverables
- normalized posting pipeline
- canonical field map
- normalization errors and fallback reasons

### Exit criteria
- ATS-originated records can be normalized end-to-end
- normalization stores enough evidence to debug extraction failures

### Evals / gates
- build `normalization_gold` dataset with labeled examples
- field-level checks for:
  - title
  - company
  - location
  - remote mode
  - salary presence or absence
- gate: no source rollout without acceptable field extraction quality

### Runnable connector quality formula

For source and parsing quality, start with a simple executable metric:

`quality = parse_rate × field_coverage × (1 - ghost_rate)`

Where:
- `parse_rate` = normalized_postings / raw_records
- `field_coverage` = weighted completeness score for critical fields
- `ghost_rate` = proportion of source output currently classified as ghost-like or stale above threshold

This is not the only metric we will ever need, but it is good enough to run on every connector iteration and spot whether a source is producing real value or mostly noise.

### Suggested field coverage formula

Use weighted field completeness for the normalized posting:

`field_coverage = 0.20*title + 0.15*company + 0.15*description + 0.15*posted_at + 0.10*location + 0.10*remote_mode + 0.10*source_url + 0.05*employment_type`

Each field is scored as:
- `1` if correctly present
- `0` if missing or clearly broken

Later we can replace binary scoring with graded field accuracy, but the first version should stay simple and runnable.

## Phase 5: Dedup and Canonical Jobs

### Objectives
- merge mirrored postings across sources into canonical jobs

### Tasks
1. Design canonical merge rules.
2. Implement exact-match dedup signals.
3. Implement heuristic dedup signals:
   - company/title similarity
   - URL/domain evidence
   - text similarity
   - time-window logic
4. Persist canonical jobs.
5. Attach postings to canonicals.

### Deliverables
- canonical job creation logic
- merge audit trail
- posting-to-canonical linkage

### Exit criteria
- obvious cross-post duplicates are collapsed
- obviously different jobs are preserved

### Evals / gates
- create `dedup_regression` dataset with:
  - must-merge pairs
  - must-not-merge pairs
- gate metrics to track:
  - false merge rate
  - missed merge rate
- strong warning: false merges are more dangerous than missed merges early on

## Phase 6: Candidate Profile and Ranking v1

### Objectives
- rank jobs for one candidate profile in an explainable way

### Tasks
1. Define candidate profile model.
2. Implement role-fit scoring.
3. Implement market-fit scoring.
4. Implement seniority-fit scoring.
5. Implement location/remote-fit scoring.
6. Implement salary-fit logic where possible.
7. Produce explanation objects for each score.

### Deliverables
- candidate profile schema
- ranking pipeline v1
- score breakdown format

### Exit criteria
- one profile can produce a top-ranked job feed
- top results are explainable and debuggable

### Evals / gates
- build `ranking_topk` labeled dataset
- evaluate top-k precision, not just subjective ranking feel
- compare against a simple baseline like chronological feed + filters
- gate: do not ship ranking changes that degrade top-of-feed quality

### Ranking metric note

`top-k precision` still matters for the ranking layer, but it should sit next to the source quality formula above rather than replace it.

The source quality formula answers: “is this connector producing worthwhile normalized data?”

Ranking precision answers: “given worthwhile data, are we surfacing the right jobs first?”

## Phase 7: Ghost-Job Detector v1

### Objectives
- introduce stale/ghost suppression without excessive false positives

### Tasks
1. Define explicit ghost signals.
2. Implement rule-based ghost score.
3. Implement reason logging per score.
4. Apply ghost penalty in ranking/delivery policy.
5. Define show/downrank/hide thresholds.

### Deliverables
- ghost signal catalog
- ghost score implementation
- decision policy for visibility

### Exit criteria
- clearly stale or evergreen jobs are penalized
- active good jobs are not aggressively hidden

### Evals / gates
- build `ghosting_precision` dataset
- label examples as:
  - active-good
  - stale
  - suspicious evergreen
  - unclear
- monitor:
  - false positive rate on good jobs
  - catch rate on stale jobs
- gate: if ghost logic hurts too many good jobs, default to downrank rather than hide

## Phase 8: Job Boards and Telegram Expansion

### Objectives
- expand coverage after core quality loops exist

### Tasks
1. Add hh.ru connector.
2. Add Wellfound / Remote OK / Habr Career / Solana jobs.
3. Add first Telegram ingestion path.
4. Extend normalization for source-specific quirks.
5. Extend dedup datasets with cross-family duplicates.

### Deliverables
- expanded source family coverage
- Telegram as a first-class input family

### Exit criteria
- new source families improve coverage without overwhelming junk rate

### Evals / gates
- source-specific ingestion smoke checks
- cross-family dedup regressions
- ranking quality re-check after source expansion
- gate: no source family rollout if it causes uncontrolled duplicate or junk growth

## Phase 9: Delivery UX

### Objectives
- turn ranked jobs into something operationally useful

### Tasks
1. Implement digest payload structure.
2. Implement inbox or feed format.
3. Add actions such as:
   - relevant
   - not relevant
   - duplicate
   - ghost likely
   - applied
4. Persist feedback events.
5. Expose match explanations.

### Deliverables
- first usable candidate-facing output
- review and feedback loop

### Exit criteria
- user can review jobs and provide structured feedback
- feedback data becomes available for future iteration

### Evals / gates
- manual usability review
- ensure feedback events are traceable to ranking and ghost decisions
- no silent action without persistent audit record

## Phase 10: Operational Hardening

### Objectives
- move from “it runs” to “it stays trustworthy”

### Tasks
1. Add source health dashboards or summaries.
2. Add broken-source triage flow.
3. Add eval regression review routine.
4. Add data refresh and dataset curation process.
5. Add rollout rules for new sources.

### Deliverables
- runbooks
- source quality playbook
- eval regression process

### Exit criteria
- we know what to do when source quality drops
- we know how to reject regressions before they leak into delivery

### Evals / gates
- source outage simulation checklist
- stale dataset refresh checklist
- post-change evaluation summary required for material ranking or ghosting changes

## 6. Pull Request Strategy

Keep PRs short and scoped to one decision or one subsystem step.

Good early PR sequence:
1. source inventory
2. implementation plan
3. source contract spec
4. canonical schema spec
5. storage model spec
6. ingestion framework skeleton
7. Greenhouse connector
8. Lever connector
9. normalization v1
10. dedup v1

PRs should avoid mixing:
- new source connector
- ranking logic change
- ghost scoring change
- dataset changes
unless the coupling is truly unavoidable.

## 7. Evaluation Milestones

We should explicitly stop and review quality at these milestones:

### Milestone A
After first ATS connectors.
Question: are we collecting real useful data or just collecting records?

### Milestone B
After normalization v1.
Question: are extracted fields trustworthy enough to support ranking?

### Milestone C
After dedup v1.
Question: are we collapsing mirrored jobs without damaging distinct openings?

### Milestone D
After ranking v1.
Question: is top-of-feed quality meaningfully better than naive search?

### Milestone E
After ghosting v1.
Question: are we actually saving review time without hiding good opportunities?

## 8. Risks To Watch

1. **Coverage without quality**
We add sources faster than we build evals.

2. **False confidence from pretty demos**
The inbox looks good but the underlying precision is poor.

3. **False merges in dedup**
We collapse different openings from the same company.

4. **Ghost overreach**
We hide good jobs because stale signals are too aggressive.

5. **Telegram noise explosion**
We treat channels as high-signal before measuring uniqueness and freshness.

## 9. Definition Of MVP Done

The MVP is done when:

1. At least one ATS family and one non-ATS family are ingested through the shared pipeline.
2. Jobs are persisted as raw records, normalized postings, and canonical jobs.
3. One candidate profile gets a ranked feed with explanations.
4. Ghost scoring exists and affects visibility policy.
5. We have data-backed eval suites for ingestion, normalization, dedup, ranking, and ghosting.
6. We have enough review confidence to tell whether a change improved or degraded system quality.
