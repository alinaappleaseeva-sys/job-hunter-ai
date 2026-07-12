# Storage

Storage holds raw records, normalized postings, canonical jobs, profile data, and evaluation artifacts.

Treat raw source payloads as first-class evidence. They are needed for debugging and eval refreshes.

## MVP scope (Phase 4.1)

| Spec table | Implementation | Module |
|---|---|---|
| `raw_source_records` (§4.4) | `save_raw`, `get_raw`, `list_raw_by_source` | `repository.py` |
| `normalized_job_postings` (§4.5) | `save_normalized`, `get_normalized`, `list_normalized_by_source` | `repository.py` |
| — | `list_unlinked_raw` (pipeline queue) | `repository.py` |

**Backend:** `MemoryJobStorage` in `memory.py` — in-process dict store for tests and smoke runs.

**Deferred:** PostgreSQL migrations, `source_runs`, canonical tables (Phase 5.1).

## Usage

```python
from datetime import datetime, timezone
from job_hunter_ai.common.models import NormalizedJobPosting, RawSourceRecord
from job_hunter_ai.storage import MemoryJobStorage

store = MemoryJobStorage()
raw_id = store.save_raw(RawSourceRecord(...))
posting_id = store.save_normalized(NormalizedJobPosting(...), raw_record_id=raw_id)
```

## Design notes

1. **`JobStorageRepository`** is a `Protocol` — normalization and dedup depend on the interface, not `MemoryJobStorage`.
2. **IDs** — `MemoryJobStorage` assigns UUIDs on `save_raw`; `save_normalized` uses `posting.posting_id` when set, otherwise generates one.
3. **Lineage** — every normalized posting must reference a `raw_record_id` (FK per storage-model §4.5).
4. **One raw → one normalized** in MVP (0..1 mapping); dedup links postings to canonicals later.

## Tests

```bash
pytest tests/unit/test_storage_memory.py -q
```