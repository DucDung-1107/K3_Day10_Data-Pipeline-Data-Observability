# Data Corruption & Recovery Report (Phase 2)

This report compares metrics and data quality across three pipeline states: **Baseline** (clean), **Corrupted** (damaged), and **Repaired** (recovered).

## 1. RAG Evaluation Metrics Comparison

| Metric | Baseline | Corrupted | Repaired | Change (Corrupt) | Recovery Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Retrieval Hit Rate** | 1.0000 | 0.5000 | 1.0000 | -0.5000 | +0.5000 |
| **Mean Token F1** | 1.0000 | 0.5506 | 1.0000 | -0.4494 | +0.4494 |
| **Judge Accuracy** | 1.0000 | 0.5417 | 1.0000 | -0.4583 | +0.4583 |
| **Mean Judge Score** | 5.0000 | 3.5417 | 5.0000 | -1.4583 | +1.4583 |

## 2. Data Quality & Freshness Comparison

| Property | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| **Quality Status** | PASS | FAIL | PASS |
| **Freshness Status** | FRESH | STALE | FRESH |
| **Row Count** | 24 | 24 | 24 |
| **Stale Rows** | 0 | 2 | 0 |

## 3. Findings & Critical Interpretations

1. **Impact of Corruption on Retrieval & Reasoning:**
   - Shows how data quality degradation directly affects retrieval hit rates and LLM reasoning accuracy.
2. **Effectiveness of Recovery:**
   - Proves that reloading and re-cleaning from the original raw source recovers RAG performance.
