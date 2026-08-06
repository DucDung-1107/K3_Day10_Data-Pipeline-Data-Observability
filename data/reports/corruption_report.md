# Corruption impact and recovery report

_Generated at 2026-08-06T04:48:37+00:00_

The three runs below share one test set, one evaluator and one top-k setting, so the
only variable is the state of the data.

## 1. Metric comparison

| Metric | Baseline | Corrupted | Repaired | Delta corrupted | Delta repaired |
| --- | ---: | ---: | ---: | ---: | ---: |
| `samples` | 24 | 24 | 24 | 0 | 0 |
| `retrieval_hit_rate` | 1.0000 | 0.6667 | 1.0000 | -0.3333 | 0.0000 |
| `mean_token_f1` | 1.0000 | 0.6737 | 1.0000 | -0.3263 | 0.0000 |
| `judge_accuracy` | 0.9583 | 0.7083 | 0.9583 | -0.2500 | 0.0000 |
| `mean_judge_score` | 4.9167 | 3.9167 | 4.9167 | -1.0000 | 0.0000 |

## 2. Reading the deltas

- `retrieval_hit_rate`: dropped by 0.3333 under corruption; repaired is back at or above baseline (1.0000).
- `mean_token_f1`: dropped by 0.3263 under corruption; repaired is back at or above baseline (1.0000).
- `judge_accuracy`: dropped by 0.2500 under corruption; repaired is back at or above baseline (0.9583).
- `mean_judge_score`: dropped by 1.0000 under corruption; repaired is back at or above baseline (4.9167).

## 3. Data quality - corrupted

- Overall: **FAIL** (5/8 checks passed)
- Rows checked: 23
- Failed checks: paper_id_unique, summary_min_length, freshness_age_days

| Check | Status | Observed | Expected |
| --- | --- | --- | --- |
| `schema_columns_present` | pass | none | no missing column |
| `row_count_minimum` | pass | 23 | >= 4 rows |
| `paper_id_not_null` | pass | 0 | 0 blank paper_id |
| `paper_id_unique` | fail | 1 | 0 duplicate paper_id |
| `title_not_empty` | pass | 0 | 0 blank titles |
| `text_for_embedding_not_empty` | pass | 0 | 0 blank text_for_embedding |
| `summary_min_length` | fail | 2 | 0 rows below 100 characters |
| `freshness_age_days` | fail | stale_rows=2, unknown_age_rows=0 | 0 rows older than 180 days |

## 4. Data quality - repaired

- Overall: **PASS** (8/8 checks passed)
- Rows checked: 24

| Check | Status | Observed | Expected |
| --- | --- | --- | --- |
| `schema_columns_present` | pass | none | no missing column |
| `row_count_minimum` | pass | 24 | >= 4 rows |
| `paper_id_not_null` | pass | 0 | 0 blank paper_id |
| `paper_id_unique` | pass | 0 | 0 duplicate paper_id |
| `title_not_empty` | pass | 0 | 0 blank titles |
| `text_for_embedding_not_empty` | pass | 0 | 0 blank text_for_embedding |
| `summary_min_length` | pass | 0 | 0 rows below 100 characters |
| `freshness_age_days` | pass | stale_rows=0, unknown_age_rows=0 | 0 rows older than 180 days |

## 5. Freshness - corrupted

- Fresh: **no** (threshold 180 days)

| Signal | Value |
| --- | ---: |
| `total_rows` | 23 |
| `latest_published` | 2026-08-01 |
| `oldest_published` | 2000-01-01 |
| `fresh_rows` | 21 |
| `stale_rows` | 2 |
| `unknown_age_rows` | 0 |
| `max_age_days` | 9714 |
| `is_fresh` | no |

## 6. Freshness - repaired

- Fresh: **yes** (threshold 180 days)

| Signal | Value |
| --- | ---: |
| `total_rows` | 24 |
| `latest_published` | 2026-08-01 |
| `oldest_published` | 2026-02-12 |
| `fresh_rows` | 24 |
| `stale_rows` | 0 |
| `unknown_age_rows` | 0 |
| `max_age_days` | 175 |
| `is_fresh` | yes |

## 7. Limits of this comparison

- Baseline quality and freshness payloads are reported in `phase1_report.md`; this
  report only carries the corrupted and repaired ones.
- A metric that did not move is evidence that the corruption did not reach it, not
  evidence that the corruption was harmless.
- Recovery is only claimed where the numbers above show it.

## 8. How to reproduce

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

