# Canonical Job Schema

This document defines the normalized and canonical data model for jobs in Job Hunter AI.

The system should distinguish between:
- a raw source record;
- a normalized posting from one source;
- a canonical job representing one logical opening across sources.

This separation is necessary so we can:
- preserve source evidence;
- debug normalization problems;
- deduplicate mirrored postings;
- rank one logical job instead of a pile of reposts;
- calculate ghost signals over time.

## 1. Design Principles

1. Preserve source truth before abstraction.
2. Treat `posting` and `canonical job` as different entities.
3. Keep enough evidence to reverse or audit dedup decisions.
4. Prefer explicit nulls over invented values.
5. Optimize for explainability, not only storage compactness.

## 2. Entity Model

The MVP data model should have three layers.

### Layer 1: Raw source record
The untouched source-level payload emitted by a connector.

### Layer 2: Normalized job posting
One source-specific posting normalized into a shared schema.

### Layer 3: Canonical job
One logical job opening that may unify multiple normalized postings from different sources.

## 3. Why Posting And Canonical Job Must Be Separate

This split is not optional.

One company opening can appear in:
- the company ATS;
- LinkedIn;
- hh.ru;
- Telegram reposts;
- ecosystem job boards.

If we collapse directly into a single record too early, we lose:
- the ability to debug source disagreements;
- the ability to inspect duplicate spread;
- the ability to reason about freshness and repost patterns;
- the ability to build ghost-job signals from posting history.

## 4. Normalized Job Posting Schema

Each normalized posting is one source-specific job artifact.

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class NormalizedJobPosting:
    posting_id: str
    source_name: str
    source_type: str
    external_id: str | None
    source_url: str | None
    company_name: str | None
    company_domain: str | None
    title_raw: str | None
    title_normalized: str | None
    description_raw: str | None
    description_text: str | None
    location_raw: str | None
    location_country: str | None
    location_region: str | None
    location_city: str | None
    remote_mode: str | None
    employment_type: str | None
    seniority: str | None
    role_family: str | None
    market: str | None
    compensation_min: float | None
    compensation_max: float | None
    compensation_currency: str | None
    posted_at: datetime | None
    discovered_at: datetime | None
    normalized_at: datetime
    content_hash: str | None
    parse_status: str
    parse_warnings: list[str]
```

## 5. Posting Field Definitions

### Identity and provenance

- `posting_id`: internal stable ID for the normalized posting.
- `source_name`: connector-level source name, such as `greenhouse`, `hh`, `telegram_tonhunt`.
- `source_type`: `ats`, `job_board`, `telegram`, `company_page`.
- `external_id`: upstream identifier where available.
- `source_url`: original URL or canonical message URL if available.

### Company fields

- `company_name`: source-normalized display name.
- `company_domain`: normalized domain if recoverable.

### Title fields

- `title_raw`: the title exactly as extracted.
- `title_normalized`: normalized title after cleanup and standardization.

### Description fields

- `description_raw`: raw HTML or source markup when useful.
- `description_text`: stripped text used for downstream NLP, dedup, and ranking.

### Location fields

- `location_raw`: source-provided location string.
- `location_country`, `location_region`, `location_city`: normalized structured location fields.
- `remote_mode`: expected values such as `remote`, `hybrid`, `onsite`, `unknown`.

### Classification fields

- `employment_type`: full-time, contract, part-time, internship, unknown.
- `seniority`: junior, mid, senior, lead, head, unknown.
- `role_family`: product, engineering, design, growth, operations, data, other.
- `market`: crypto, fintech, SaaS, infra, consumer, unknown.

### Compensation fields

- `compensation_min`, `compensation_max`, `compensation_currency`: parsed structured compensation where possible.

### Time fields

- `posted_at`: source-stated posting time if available.
- `discovered_at`: when our system first observed the record.
- `normalized_at`: when normalization completed.

### Parsing diagnostics

- `content_hash`: content fingerprint for drift, dedup hints, and repost tracking.
- `parse_status`: `parsed`, `partial`, `failed`.
- `parse_warnings`: list of field-level or source-level concerns.

## 6. Canonical Job Schema

The canonical job represents one logical opening after dedup.

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class CanonicalJob:
    canonical_job_id: str
    primary_posting_id: str
    company_name: str | None
    company_domain: str | None
    title_normalized: str | None
    role_family: str | None
    seniority: str | None
    market: str | None
    remote_mode: str | None
    employment_type: str | None
    location_country: str | None
    location_region: str | None
    location_city: str | None
    compensation_min: float | None
    compensation_max: float | None
    compensation_currency: str | None
    canonical_posted_at: datetime | None
    first_seen_at: datetime
    last_seen_at: datetime
    active_posting_count: int
    source_count: int
    ghost_score: float | None
    canonical_status: str
    merge_confidence: float | None
    merge_reasons: list[str]
```

## 7. Canonical Field Semantics

### Identity

- `canonical_job_id`: stable logical ID for one opening.
- `primary_posting_id`: the posting chosen as the representative record for display or downstream explanation.

### Consolidated fields

These are the “best known” fields for the logical opening after comparing postings.

- `company_name`
- `company_domain`
- `title_normalized`
- `role_family`
- `seniority`
- `market`
- `remote_mode`
- `employment_type`
- `location_country`
- `location_region`
- `location_city`
- `compensation_min`
- `compensation_max`
- `compensation_currency`

### Time and spread fields

- `canonical_posted_at`: best estimate of the job’s posting time.
- `first_seen_at`: first time any linked posting was observed.
- `last_seen_at`: latest observation among linked postings.
- `active_posting_count`: active linked postings.
- `source_count`: number of distinct sources linked to the canonical job.

### Quality and dedup fields

- `ghost_score`: current ghost/stale estimate at canonical level.
- `canonical_status`: `active`, `stale`, `closed`, `uncertain`.
- `merge_confidence`: optional score for how confident we are in the dedup cluster.
- `merge_reasons`: explicit reasons why postings were merged.

## 8. Primary Posting Selection

Every canonical job should nominate one `primary_posting_id`.

Suggested priority order:
1. ATS or direct company posting
2. source with strongest field completeness
3. source with most trustworthy compensation/location fields
4. newest active posting

The primary posting is used for:
- UI rendering
- explanations
- fallback source URL
- human review

It should be replaceable without changing the canonical job identity.

## 9. Canonical Merge Rules

Canonical creation should rely on evidence, not only text similarity.

Useful merge signals:
- same company domain
- same or highly similar normalized title
- highly similar description fingerprint
- close time window
- matching external or source identity hints
- known repost path from source family

Merge decisions should always be auditable.

## 10. Canonical Merge Audit Record

The system should preserve a merge explanation record, even if the first implementation is simple.

Example fields:

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class CanonicalMergeEvent:
    canonical_job_id: str
    posting_id: str
    merged_at: datetime
    merge_confidence: float | None
    merge_reasons: list[str]
    reviewer_override: bool = False
```

This is important because bad merges are expensive and hard to notice later.

## 11. How Ghost Signals Use The Schema

Ghost and stale detection should operate at both levels.

### Posting-level signals
- posting age
- source-specific freshness
- last material content change
- broken apply path

### Canonical-level signals
- repeated re-opening across time
- too many near-identical reposts
- long-lived presence with minimal change
- mismatch between spread and hiring evidence

This is another reason the posting/canonical split must exist.

## 12. Required Fields For Ranking

For ranking to work reasonably well, a canonical job should ideally have:
- `title_normalized`
- `company_name`
- `role_family`
- `seniority`
- `market`
- one of `remote_mode` or structured location
- one usable description text source via its primary posting

Compensation is highly valuable but should not be required for the job to exist.

## 13. Null And Unknown Handling

The schema should differentiate:
- missing because the source did not provide it;
- missing because parsing failed;
- missing because not yet inferred.

In the first version, this can be represented with:
- nullable field values
- `parse_status`
- `parse_warnings`

Later we can add explicit field provenance if needed.

## 14. Evaluation Implications

The schema is intentionally designed to support evals.

### For normalization evals
We can grade field extraction at the posting level.

### For dedup evals
We can grade must-merge and must-not-merge examples at the canonical level.

### For ghost evals
We can calculate posting-level and canonical-level stale patterns separately.

### For ranking evals
We can rank canonicals rather than duplicated postings.

## 15. Acceptance Criteria For Schema Adoption

The canonical schema is ready to use when:

1. every connector can produce raw records that normalize into the posting shape;
2. normalized postings preserve enough evidence for debugging;
3. canonical jobs can unify duplicates without losing posting provenance;
4. ranking and ghosting inputs are representable without schema hacks;
5. field-level normalization evals and dedup evals can be built directly on the schema.

## 16. Relationship To Other Specs

This document depends on:
- `docs/specs/source-contract.md`

This document should feed into:
- storage model spec
- dedup rules spec
- ranking inputs spec
- ghost-job scoring spec
