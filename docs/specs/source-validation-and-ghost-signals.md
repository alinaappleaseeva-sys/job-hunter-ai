# Source Validation And Ghost Signals

This document defines source-validation checks and ghost-signal rules for suspicious vacancies, especially those originating from aggregators, repost channels, or other secondary surfaces.

The trigger for this spec is simple:

- a vacancy appears on an aggregator;
- the listing has description text and looks real enough;
- but the apply path is broken, empty, misleading, or dead;
- and the same vacancy does not exist on the company site or known primary source.

This is a high-value ghosting case. We should not treat such listings as normal jobs until they are validated.

## 1. Goals

This spec should help us:

1. identify likely ghost or stale listings early;
2. distinguish primary sources from secondary or aggregator sources;
3. validate whether an aggregator vacancy is actually grounded in a real company opening;
4. produce explainable ghost signals, not just opaque flags;
5. reduce junk review time without hiding too many good jobs.

## 2. Core Principle

Aggregator-origin jobs should not be trusted by default.

If a vacancy is found on a secondary source such as an aggregator, repost board, or Telegram repost channel, the system should try to confirm whether the vacancy exists on a primary source.

Primary sources are usually:
- company career pages
- ATS postings
- company-owned application flows

Secondary sources are usually:
- aggregators
- repost boards
- ecosystem digests
- Telegram repost channels

Rule of thumb:

`secondary-source vacancy without source-of-truth confirmation => suspicious by default`

## 3. Source Roles

Every source should eventually carry a `source_role` classification.

Suggested values:
- `primary`
- `secondary`
- `repost_channel`
- `unknown`

### Examples

- Greenhouse posting: `primary`
- company career page: `primary`
- Jobstash-like board: `secondary`
- Telegram channel reposting third-party jobs: `repost_channel`

This role does not decide ranking by itself, but it changes how much validation we require.

## 4. Validation Layers

We should validate suspicious listings in layers.

### Layer A: Apply target health
Question: does the apply path actually lead somewhere meaningful?

### Layer B: Primary-source confirmation
Question: can we find evidence of the same vacancy on the company site or ATS?

### Layer C: Freshness consistency
Question: do the timestamps and availability signals line up across sources?

### Layer D: Canonical source confidence
Question: do we know which source should be treated as the source of truth?

## 5. Apply Target Health Checks

These checks should run for any vacancy with an apply path.

## 5.1 Basic checks

- apply URL exists
- apply URL is syntactically valid
- apply URL is not obviously malformed
- apply URL does not point to an empty placeholder

## 5.2 HTTP and redirect checks

- returns `200` or expected success path
- does not terminate in `404`, `410`, `5xx`
- does not redirect to an unrelated or generic page
- does not redirect to home page when a job page is expected
- does not redirect to a dead intermediate page

## 5.3 Semantic landing checks

Even if the HTTP response is technically healthy, the page may still be bad.

The landing page should be checked for:
- job-specific title or slug match
- presence of application UI or job content
- absence of generic “page not found” or empty shell states
- absence of unrelated company landing content without job details

## 5.4 Apply health outcomes

Suggested values:
- `healthy`
- `missing`
- `broken_http`
- `redirect_non_job`
- `generic_company_page`
- `empty_or_placeholder`
- `unknown`

## 6. Primary-Source Confirmation Checks

If a listing originates from a secondary source, we should try to confirm it on a primary source.

## 6.1 Confirmation targets

Try in this rough order:

1. direct company career page
2. known ATS page for the company
3. canonical company jobs page if available
4. other trusted primary source owned by the company

## 6.2 Confirmation strategies

Possible confirmation methods:
- exact URL mapping from aggregator to ATS
- exact title match on company jobs page
- strong title + company + location match
- source-provided `apply_url` pointing to the company ATS
- structured ATS identifiers embedded in the source listing

## 6.3 Confirmation outcomes

Suggested values:
- `confirmed_exact`
- `confirmed_strong_match`
- `career_site_exists_but_job_missing`
- `career_site_missing`
- `ats_known_but_job_missing`
- `no_primary_source_found`
- `unknown`

## 7. Aggregator-Only Vacancy Pattern

This pattern should be treated as a first-class ghost signal.

Definition:

- source role is `secondary` or `repost_channel`
- no valid primary-source confirmation found
- and/or apply target is broken or generic

This pattern often means:
- stale scraper residue
- expired job still living on aggregator cache
- phantom listing copied from an old source
- low-quality board ingestion with no source-of-truth reconciliation

## 8. Ghost Signals For This Class Of Cases

Suggested explicit ghost signals:

- `apply_link_missing`
- `apply_link_broken`
- `apply_link_redirects_to_non_job_page`
- `apply_link_lands_on_generic_company_page`
- `secondary_source_only`
- `no_confirmed_primary_source`
- `career_site_exists_but_job_missing`
- `known_ats_exists_but_job_missing`
- `freshness_mismatch_between_sources`
- `stale_secondary_listing`

These signals should be recorded individually, not only collapsed into one score.

## 9. Example Weighting For Ghost Score

The exact weights can change later, but a first explainable version could look like this:

- `apply_link_missing`: `+0.20`
- `apply_link_broken`: `+0.35`
- `apply_link_redirects_to_non_job_page`: `+0.30`
- `apply_link_lands_on_generic_company_page`: `+0.25`
- `secondary_source_only`: `+0.20`
- `no_confirmed_primary_source`: `+0.25`
- `career_site_exists_but_job_missing`: `+0.25`
- `known_ats_exists_but_job_missing`: `+0.25`
- `freshness_mismatch_between_sources`: `+0.10`

Interpretation:
- low score: probably safe enough to show
- medium score: downrank and mark suspicious
- high score: hide by default or require stronger confirmation

## 10. Validation Pipeline Position

These checks should not live inside connector code.

Recommended flow:

1. connector fetches source record
2. record is normalized into posting
3. system classifies source role
4. validation service runs apply-link and source-of-truth checks
5. validation signals are stored
6. ghosting layer consumes those signals
7. ranking and delivery apply visibility policy

This keeps acquisition logic separate from trust logic.

## 11. New Validation Artifacts To Persist

The storage model should eventually support structured validation results.

Minimum fields we should persist somewhere per posting or canonical job:
- `source_role`
- `apply_health_status`
- `apply_health_notes`
- `primary_source_confirmation_status`
- `primary_source_url`
- `validation_checked_at`
- `validation_signals`

These can start as JSON fields if we want to move fast, but they must be queryable.

## 12. Decision Policy

Suggested first decision policy:

### If source is primary
- no extra suspicion by default
- still run apply health checks where relevant

### If source is secondary and apply is healthy and primary is confirmed
- allow normal ranking

### If source is secondary and apply is healthy but no primary source is found
- downrank by default
- keep visible only if other quality signals are strong

### If source is secondary and apply is broken or generic and no primary source is found
- mark as strong ghost candidate
- hide or aggressively downrank

## 13. Example Case: Aggregator Vacancy With Dead Apply Flow

Example pattern similar to the motivating case:

- source: web3 aggregator
- listing page exists
- job description exists
- apply click goes nowhere useful
- company site exists but has no such vacancy

Expected outputs:
- `source_role = secondary`
- `apply_health_status = broken_http` or `generic_company_page`
- `primary_source_confirmation_status = career_site_exists_but_job_missing`
- ghost signals include:
  - `apply_link_broken`
  - `no_confirmed_primary_source`
  - `career_site_exists_but_job_missing`

This should almost certainly not be treated as a normal healthy vacancy.

## 14. Evaluation Implications

We should create eval datasets specifically for validation and ghost signals.

Useful labeled classes:
- `primary_healthy`
- `secondary_confirmed`
- `secondary_unconfirmed`
- `broken_apply`
- `career_site_missing_job`
- `secondary_stale`

Useful metrics:
- precision on ghost candidates
- false positive rate on healthy secondary jobs
- confirmation rate of secondary-source listings
- broken apply detection rate

## 15. Acceptance Criteria For This Layer

This validation layer is useful when:

1. secondary-source jobs are no longer trusted by default;
2. broken apply flows are detected automatically;
3. we can distinguish “unconfirmed” from “confirmed” aggregator vacancies;
4. ghosting decisions can cite explicit validation signals;
5. the system materially reduces junk listings from aggregator-style sources.

## 16. Relationship To Other Specs

This document depends on:
- `docs/specs/source-contract.md`
- `docs/specs/canonical-job-schema.md`
- `docs/specs/storage-model.md`

This document should inform:
- ghost-job scoring spec
- storage additions for validation signals
- ranking visibility policy
- connector rollout rules for secondary sources

