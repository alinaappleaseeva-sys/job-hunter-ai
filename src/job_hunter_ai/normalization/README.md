# Normalization

Normalization converts source-specific `RawSourceRecord` objects into the shared `NormalizedJobPosting` schema (`docs/specs/canonical-job-schema.md`).

Any field extraction change must be backed by field-level evaluation data (`evals/datasets/normalization_gold/`).

## Pipeline flow (v1)

```
RawSourceRecord[]
    │
    ▼
normalize_postings(records, store=?)
    │
    ├─► [optional] store.save_raw(record)  → raw_record_id
    │
    ├─► registry.get_mapper(source_name)
    │       ├─ None → failed + unsupported_provider
    │       └─ BaseMapper.normalize(record)
    │
    ├─► [optional] store.save_normalized(posting, raw_record_id=...)
    │
    └─► NormalizationRunResult (counts + per-item diagnostics)
```

## Module layout

| Module | Role |
|---|---|
| `pipeline.py` | `normalize_postings()`, `normalize_record()` entrypoints |
| `registry.py` | `source_name` → provider mapper lookup |
| `mappers/base.py` | `BaseMapper` ABC |
| `mappers/` | Provider implementations (Greenhouse, Lever, Ashby — Step 4.4) |
| `fields/` | Shared field normalizers (Step 4.3) — see table below |
| `types.py` | `NormalizationRunResult`, `ParseDiagnostics` |

## Field normalizers (`fields/`)

Reusable helpers consumed by provider mappers (Step 4.4). Each function is unit-tested against `normalization_gold` labels where applicable.

| Module | Functions | Purpose |
|---|---|---|
| `title.py` | `normalize_title()` | Trim + lowercase title for dedup/ranking |
| `description.py` | `html_to_text()`, `pick_description()` | HTML → plain text; choose best description candidate |
| `employment.py` | `normalize_employment_type()` | Map provider strings (`FullTime`, `Regular Full Time`) → canonical enum |
| `company.py` | `extract_company_domain()` | Hostname from job/company URL |
| `location.py` | `parse_location_string()` | City/state/country parsing + `ParsedLocation` dataclass |
| `remote.py` | `normalize_remote_mode()` | Infer `remote` / `hybrid` / `onsite` / `unknown` from workplace + location signals |
| `compensation.py` | `parse_ashby_compensation()`, `parse_salary_summary_text()` | Salary range extraction |
| `enrichment.py` | `infer_seniority()`, `infer_role_family()`, `infer_market()` | Title/company heuristics for diagnostic fields |

## Parse status rules

| Status | When |
|---|---|
| `parsed` | All required core fields present; no blocking warnings |
| `partial` | Usable posting with documented missing fields |
| `failed` | No mapper, mapper error, or unusable record |

**Step 4.2** ships the skeleton only — no ATS mappers registered yet. All records return `failed` + `unsupported_provider` until Step 4.4.

## Storage lineage

When `store` is provided:

1. `save_raw(record)` → `raw_record_id`
2. `save_normalized(posting, raw_record_id=...)` → `posting_id`

Maps to `docs/specs/storage-model.md` §4.4–4.5.

## Public API

```python
from job_hunter_ai.normalization import normalize_postings
from job_hunter_ai.storage import MemoryJobStorage

result = normalize_postings(records, store=MemoryJobStorage())
```

## Tests

```bash
pytest tests/unit/test_normalization_pipeline.py tests/unit/test_normalization_fields.py -q
```

## Eval gate

Gold dataset harness lands in Step 4.5 (`evals/suites/normalization_v1.yaml`).