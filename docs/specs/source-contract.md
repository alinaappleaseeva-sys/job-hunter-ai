# Source Contract

This document defines the contract for all job-source connectors.

The purpose of the contract is to make every source integrate through the same pipeline and to make source quality measurable. A connector is not considered complete because it fetches pages or messages. It is complete only when it emits records in the expected shape and produces enough signal for downstream evaluation.

## 1. Contract Goals

Every connector should:

1. fetch source data reproducibly;
2. preserve raw source evidence;
3. emit one shared raw-record format;
4. expose source-level run metadata;
5. support source-quality evaluation;
6. fail in observable ways.

## 2. Connector Boundaries

### Connector is responsible for
- accessing the source;
- fetching records or messages;
- preserving source identity and fetch metadata;
- producing raw records in the standard format;
- reporting run telemetry and errors.

### Connector is not responsible for
- ranking;
- ghost-job scoring;
- final canonical dedup decisions;
- candidate profile matching;
- product-facing delivery formatting.

Connectors should stay narrow. If business logic leaks into connector code, source quality becomes harder to reason about and much harder to evaluate.

## 3. Source Families

The contract must support four source families:

- ATS platforms
- job boards
- Telegram channels
- direct company career pages

All four emit into the same raw record shape, even if the acquisition method differs.

## 4. Raw Source Record

Each fetchable job-like item must be emitted as one `RawSourceRecord`.

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class RawSourceRecord:
    source_name: str
    source_type: str
    record_type: str
    external_id: str | None
    source_url: str | None
    fetched_at: datetime
    discovered_at: datetime | None
    payload: dict[str, Any]
    content_hash: str | None
    cursor_value: str | None
    metadata: dict[str, Any]
```

## 5. Field Definitions

### Required fields

These fields are required for every emitted raw record:

- `source_name`
- `source_type`
- `record_type`
- `fetched_at`
- `payload`
- `metadata`

### Strongly recommended fields

These fields should be emitted whenever the source gives enough information:

- `external_id`
- `source_url`
- `discovered_at`
- `content_hash`
- `cursor_value`

### Source type values

Allowed values:
- `ats`
- `job_board`
- `telegram`
- `company_page`

### Record type values

Initial allowed values:
- `job_posting`
- `message`
- `company_listing`

`company_listing` is useful for sources that may need a second-stage crawl to reach actual jobs.

## 6. Metadata Requirements

`metadata` must be source-specific but should always support debugging.

Expected metadata keys where available:
- `http_status`
- `channel_handle`
- `page_number`
- `cursor_type`
- `cursor_value`
- `provider`
- `fetched_via`
- `language_hint`

Examples:

### ATS connector metadata
```json
{
  "provider": "greenhouse",
  "cursor_type": "page",
  "cursor_value": "3",
  "fetched_via": "jobs_api"
}
```

### Telegram connector metadata
```json
{
  "channel_handle": "tonhunt",
  "cursor_type": "message_id",
  "cursor_value": "1842",
  "fetched_via": "telegram_api"
}
```

## 7. Source Run Contract

Each connector run should also emit a `SourceRunResult`-style summary.

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class SourceRunResult:
    source_name: str
    started_at: datetime
    finished_at: datetime
    success: bool
    records_fetched: int
    records_emitted: int
    records_persisted: int
    cursor_before: str | None
    cursor_after: str | None
    error_type: str | None
    error_message: str | None
```

This makes connector runs auditable and gives evals something concrete to consume.

## 8. Fetch Semantics

All connectors should support these behaviors where applicable:

1. `initial_backfill`
2. `incremental_fetch`
3. `resume_from_cursor`
4. `idempotent_replay` for already seen records

Not every source will implement them in the same way, but the runtime should assume these lifecycle states exist.

## 9. Connector Quality Metrics

Each connector should produce a runnable quality score.

Primary metric:

`quality = parse_rate × field_coverage × (1 - ghost_rate)`

### 9.1 Parse rate

`parse_rate = normalized_postings / raw_records`

Interpretation:
- if a connector fetches many records but almost none can be normalized into job postings, it is low-value or broken;
- if `parse_rate` drops after a source change, we should treat that as a regression.

### 9.2 Field coverage

`field_coverage` is the weighted completeness score over normalized records.

Suggested first version:

`field_coverage = 0.20*title + 0.15*company + 0.15*description + 0.15*posted_at + 0.10*location + 0.10*remote_mode + 0.10*source_url + 0.05*employment_type`

Each component is:
- `1` if correctly present
- `0` if missing or clearly unusable

This should remain simple at first. We can later split completeness from correctness if needed.

### 9.3 Ghost rate

`ghost_rate = suspected_ghost_or_stale_records / normalized_postings`

Interpretation:
- a high `ghost_rate` does not always mean the connector is broken;
- but it does mean the source may be low-value for MVP review workflows;
- a connector with acceptable parsing but very high ghost rate should be reconsidered before rollout.

### 9.4 Why this metric exists

The metric answers a practical question:

“Is this source producing enough usable and trustworthy job data to justify its maintenance cost?”

It is not a replacement for ranking metrics.

## 10. Required Normalization Inputs

For a connector to be considered useful, it should usually provide enough raw evidence for normalization to recover these downstream fields when the source actually exposes them:

- title
- company
- description
- posted date or freshness proxy
- location
- remote mode or location constraints
- source URL
- external ID or stable identity hint

If a source consistently fails to expose most of these, it may remain a research source but should not be treated as a priority ingestion source.

## 11. Error Handling Requirements

Connectors must distinguish at least these failure classes:

- network failure
- auth failure
- anti-bot or rate-limit response
- schema drift or parser break
- empty successful response
- partial fetch with continuation possible

These should be logged in machine-readable form so operations and eval review can tell the difference between “source is empty” and “connector is broken”.

## 12. Anti-Bot and Hard-Access Sources

Some sources require special treatment.

Examples:
- LinkedIn may require third-party enrichment or infrastructure such as Proxycurl.
- hh.ru may require anti-bot-aware acquisition strategy.
- Ashby may require careful rate limiting and retry policy.

For these sources, the connector spec must include:
- acquisition constraints
- retry policy
- backoff policy
- legal/operational review note if needed

We should not let “strategically important” override “operationally expensive” without explicit justification.

## 13. Fixture Requirements

Every connector PR should include at least one of:
- recorded sample payloads
- fixture responses
- message snapshots
- company-page HTML examples

Without fixtures, source regressions are too easy to miss.

## 14. Acceptance Checklist For A New Source

A new source is ready to move beyond experiment stage when:

1. it emits `RawSourceRecord` objects in the standard shape;
2. connector run summary is available;
3. at least one fixture or sample exists;
4. `parse_rate` is measurable;
5. `field_coverage` is measurable;
6. `ghost_rate` is measurable or estimable;
7. the resulting quality score is reviewable;
8. the source adds meaningful coverage, freshness, or uniqueness relative to existing sources.

## 15. Relationship To Other Specs

This contract should stay upstream of:
- canonical job schema
- storage model
- dedup rules
- ranking inputs
- ghost-job scoring inputs

Those specs should depend on this document, not the other way around.

