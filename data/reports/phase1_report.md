# Baseline Data Pipeline Report (Phase 1)

This report details the execution and validation of the baseline RAG data pipeline.

## 1. Ingestion Metrics

| Property | Value |
| --- | --- |
| Source API | Crossref REST API |
| Query | `agentic retrieval augmented generation large language model` |
| Filter | `from-pub-date:2026-02-07,has-abstract:true` |
| Raw Records Fetched | 24 |
| Cleaned Records Output | 24 |

## 2. Evaluation Metrics

| Metric | Value | Interpretation |
| --- | --- | --- |
| **Retrieval Hit Rate** | 0.8333 | Proportion of queries where the ground truth document was retrieved |
| **Mean Token F1** | 0.8824 | Word-level overlap between predicted and reference answers |
| **Judge Accuracy** | 0.8750 | Proportion of answers judged correct (materially correct) |
| **Mean Judge Score** | 4.5417 | Average quality score (1 to 5) given by the evaluator |

## 3. Data Quality Validation

- **Overall Quality Success**: `PASS`
- **Timestamp**: `2026-08-06T03:41:35.860286+00:00`

### Checks Executed:
- **Has Rows**: `PASS` (Total: 24)
- **No Missing Titles**: `PASS` (Missing: 0)
- **No Missing Summaries**: `PASS` (Missing: 0)
- **No Duplicates**: `PASS` (Duplicates: 0)
- **No Short Summaries**: `PASS` (Short < 100 char: 0)
- **No Negative Age**: `PASS` (Negative: 0)

## 4. Freshness Monitoring

- **Status**: `FRESH`
- **Oldest Publication Date**: `2026-02-12`
- **Latest Publication Date**: `2026-08-01`
- **Stale Rows (exceeding 180 days)**: 0 / 24
