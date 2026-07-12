# Dedup

Dedup merges mirrored postings into a canonical job while preserving source-specific evidence.

This module should optimize for auditability. Wrong merges are expensive and often hard to notice without evals.

## Phase 5 Implementation (v1)

- **Models**: `CanonicalJob`, `CanonicalMergeEvent` (defined in `common/models.py`)
- **Logic location**: `dedup/service.py`
- **API**: `deduplicate_postings(postings, store=None) -> DedupResult`
- **Signals**:
  - Exact: `content_hash` match OR `(company_domain or normalized_company, title_normalized)` exact equality
  - Heuristic: title + company similarity via `difflib.SequenceMatcher` (thresholds ~0.82 title / 0.65 company)
- **Primary selection**: ATS/company source type preferred + field completeness score
- **Persistence**: when `store` (JobStorageRepository) is passed:
  - `save_canonical`
  - `link_posting_to_canonical` (join table `canonical_job_postings` equivalent)
  - `save_merge_event`
- **In-memory backend**: `MemoryJobStorage` fully implements the extended protocol
- **Types**: `DedupResult`, `DedupMatch` in `dedup/types.py`

## Usage example

```python
from job_hunter_ai.dedup import deduplicate_postings
from job_hunter_ai.storage import MemoryJobStorage

store = MemoryJobStorage()
# ... normalize postings ...
result = deduplicate_postings(normalized_postings, store=store)
print(len(result.canonicals), "canonical jobs from", result.posting_count, "postings")
```

See unit tests in `tests/unit/test_dedup_service.py` and storage tests for linkage verification.
