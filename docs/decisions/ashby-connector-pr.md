# PR: Ashby posting API connector (Tier 2)

**Branch:** `draft/ashby-connector` → `main`  
**Title:** `feat(connectors): Ashby posting API connector (Tier 2)`

## What

Adds `AshbyConnector` — third ATS connector, aligned with Greenhouse and Lever on the shared `FetchResult` contract from `base.py`.

Also extracts shared `HttpxDirectClient` into `connectors/http_client.py` (used by Greenhouse, Lever, and Ashby).

## Connector comparison (Greenhouse / Lever / Ashby)

| | Greenhouse | Lever | Ashby |
|---|---|---|---|
| **Tier** | 1 | 1–2 | **2** (rate-limited) |
| **Endpoint** | `boards-api.greenhouse.io/.../jobs` | `api.lever.co/v0/postings/{site}` | `api.ashbyhq.com/posting-api/job-board/{client}` |
| **Auth** | None (public Job Board API) | None (public Postings API) | None (public posting API) |
| **Pagination** | None (full board in one response) | `skip`/`limit` (auto-drained) | None (full board in one request) |
| **Response shape** | `{"jobs": [...], "meta": {...}}` | Top-level JSON array (or `{"data": [...]}`) | `{"jobs": [...], "apiVersion": "1"}` |
| **`fetch()` return** | `FetchResult` | `FetchResult` | `FetchResult` |
| **Imports** | `common.models.RawSourceRecord` | `common.models.RawSourceRecord` | `common.models.RawSourceRecord` |
| **HTTP client** | `HttpxDirectClient` (shared) | `HttpxDirectClient` (shared) | `HttpxDirectClient` (shared) |
| **Rate-limit policy** | Single GET, 429 → scheduler backoff | Single GET per page, 429 → scheduler backoff | **Single GET, no retry**; scheduler must serialize boards |
| **`run_metadata` extras** | `board_total`, `raw_job_count` | `pages_fetched`, `page_size` | `rate_limit_tier: "tier_2"`, `api_version` |
| **Company field** | `company_name` in payload | Site slug in metadata | Board slug (`client_name`) as proxy |
| **Employment type** | Not on Board API | `categories.commitment` | `employmentType` |
| **Remote mode** | Not on Board API | `workplaceType` / `categories.remote` | `workplaceType` / `isRemote` |
| **Tests** | 14 connector + 1 quality smoke | 16 connector + 1 quality smoke | **16 connector + 1 quality smoke** |
| **Fixture** | 20 Stripe postings | 20 leverdemo postings | **64 Ashby postings** |

## Rate-limit note (reviewer attention)

Ashby is **Tier 2** per `implementation-plan.md`:

- One HTTP request per `fetch()` — no internal retry loop.
- Scheduler must **serialize** Ashby board fetches and honor `ConnectorRateLimitError` + `retry-after` header.
- Prefer poll intervals of several minutes per board.

## Test plan

```bash
pytest tests/ -q
# → 59 passed
```

Coverage:

- [x] Happy path (64-posting fixture)
- [x] Empty board / schema errors / rate limit / network errors
- [x] Malformed job entries skipped (parse_rate signal)
- [x] Payload field-presence smoke test for downstream normalization
- [x] Shared `HttpxDirectClient` regression via existing GH/Lever/Ashby tests

## Depends on (already merged)

- Connector base contract (#9)
- Connector quality helpers (#10)
- Greenhouse connector (#7)
- Lever connector (#11)

## Post-merge scheduler guidance

- Do **not** parallelize requests to `api.ashbyhq.com`.
- Back off on `ConnectorRateLimitError`; read `retry-after` from error message.
- Ashby boards can be polled less frequently than Greenhouse/Lever.