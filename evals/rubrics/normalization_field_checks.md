# Normalization field checks rubric

Grading criteria for the `normalization_gold` dataset and `normalization_v1` suite.

Aligned with:
- `docs/specs/canonical-job-schema.md` §4–5
- `docs/architecture/implementation-plan.md` §Phase 4 (field_coverage formula)

## 1. What we grade

For each gold example, compare **predicted** `NormalizedJobPosting` fields against **labeled** expectations in `examples.jsonl`.

### Core fields (gate metrics)

| Field | Weight in field_coverage | Gate threshold |
|---|---|---|
| `title_normalized` | 0.20 | ≥ 90% exact match |
| `company_name` | 0.15 | ≥ 90% exact match |
| `description_text` | 0.15 | ≥ 80% present when labeled present |
| `posted_at` | 0.15 | ≥ 75% present when labeled present |
| `location_raw` | 0.10 | ≥ 85% exact/contains |
| `remote_mode` | 0.10 | ≥ 80% enum match |
| `source_url` | 0.10 | ≥ 95% present (from raw record) |
| `employment_type` | 0.05 | ≥ 75% when label is non-null |

### Diagnostic fields (tracked, not gated in v1)

- `seniority`, `role_family`, `market`
- `location_country`, `location_region`, `location_city`
- `compensation_min`, `compensation_max`, `compensation_currency`
- `parse_warnings` (set overlap, not strict order)

## 2. Grading modes

Each example specifies per-field grading in `grading`:

### `exact`

Predicted value must equal label (after normalization pipeline output).  
Use for: `title_normalized`, `company_name`, `employment_type`, `parse_status`, `role_family`, `seniority`.

### `enum`

Predicted value must be in:

```
remote_mode: remote | hybrid | onsite | unknown
employment_type: full-time | part-time | contract | internship | unknown | null
parse_status: parsed | partial | failed
role_family: product | engineering | design | growth | operations | data | sales | other | null
seniority: junior | mid | senior | lead | head | unknown | null
```

### `absent`

Predicted field must be `null` or empty string.

### `present`

Predicted field must be non-null and non-empty.

### `contains`

Label is a substring of predicted (or vice versa for `location_raw` multi-hub strings).  
Use when gold label is intentionally shorter than source text.

### `warning_superset`

Every label warning must appear in predicted `parse_warnings` (predicted may have extras).

## 3. Parse status rules

| Status | When |
|---|---|
| `parsed` | All required core fields extracted; no blocking warnings |
| `partial` | Job is usable but ≥1 expected field missing with documented warning |
| `failed` | Cannot produce a usable posting (e.g. missing title) |

**Required for `parsed`:** `title_normalized`, `company_name`, `description_text` (non-empty), `source_url`.

**Typical `partial` triggers:**
- `employment_type_missing` (Greenhouse Board API)
- `location_missing`
- `multi_location` (ambiguous hub list)
- `compensation_unparsed`

**Typical `failed` triggers:**
- `title_missing`
- `malformed_payload`
- `unsupported_provider`

## 4. Acceptable fallbacks vs errors

| Situation | Acceptable? | Grade |
|---|---|---|
| Source omits employment type; warning emitted | Yes | `partial`, employment `absent` |
| Invented company name not in source/metadata | No | fail `company_name` |
| `unknown` remote_mode when source silent | Yes | enum pass |
| Wrong country inference (US vs GB) | No | fail `location_country` |
| Hallucinated salary | No | fail compensation fields |

## 5. Scoring per example

```
example_pass = all graded fields pass per their grading mode
suite_accuracy(field) = passes / examples where field is graded
```

Synthetic negative `norm-syn-001` must always predict `parse_status=failed`.

## 6. Regression policy

- **Block merge** if any gate threshold in `normalization_v1.yaml` fails.
- **Warn** (non-blocking) if diagnostic fields drop >5% vs last eval run.
- Normalization PRs that change mappers must update gold labels in the same PR or document why labels are unchanged.

## 7. Connector quality linkage

After normalization, connector quality uses normalized postings:

```
quality = parse_rate × field_coverage × (1 - ghost_rate)
```

where `field_coverage` on normalized postings uses the weights in §1.  
This rubric is the authoritative definition of per-field pass/fail for `field_coverage` evals.