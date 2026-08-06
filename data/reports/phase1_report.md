# Phase 1 - Baseline report

_Generated at 2026-08-06T04:31:33+00:00_

Every number below is rendered from the artifacts written by this run; nothing is
typed in by hand.

## 1. Source

| Source field | Value |
| --- | --- |
| `source_api` | Crossref REST API |
| `query` | agentic retrieval augmented generation large language model |
| `filter` | from-pub-date:2026-02-07,has-abstract:true |
| `raw_records` | 24 |

## 2. Evaluation metrics

| Metric | Value |
| --- | ---: |
| `samples` | 24 |
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 1.0000 |
| `judge_accuracy` | 1.0000 |
| `mean_judge_score` | 5 |

### Ragas

_Skipped: Set RUN_RAGAS=1 to enable the slower Ragas pass._

## 3. Data quality

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

## 4. Freshness

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

## 5. How to reproduce

```bash
uv run python script/run_phase1.py
```

