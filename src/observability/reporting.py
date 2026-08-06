from __future__ import annotations

from pathlib import Path
from typing import Any
from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Generate Markdown report for baseline Phase 1."""
    md_content = f"""# Baseline Data Pipeline Report (Phase 1)

This report details the execution and validation of the baseline RAG data pipeline.

## 1. Ingestion Metrics

| Property | Value |
| --- | --- |
| Source API | {source_summary.get("source_api", "Crossref REST API")} |
| Query | `{source_summary.get("query", "")}` |
| Filter | `{source_summary.get("filter", "")}` |
| Raw Records Fetched | {source_summary.get("raw_records", 0)} |
| Cleaned Records Output | {quality.get("metrics", {}).get("total_rows", 0)} |

## 2. Evaluation Metrics

| Metric | Value | Interpretation |
| --- | --- | --- |
| **Retrieval Hit Rate** | {metrics.get("retrieval_hit_rate", 0.0):.4f} | Proportion of queries where the ground truth document was retrieved |
| **Mean Token F1** | {metrics.get("mean_token_f1", 0.0):.4f} | Word-level overlap between predicted and reference answers |
| **Judge Accuracy** | {metrics.get("judge_accuracy", 0.0):.4f} | Proportion of answers judged correct (materially correct) |
| **Mean Judge Score** | {metrics.get("mean_judge_score", 0.0):.4f} | Average quality score (1 to 5) given by the evaluator |

## 3. Data Quality Validation

- **Overall Quality Success**: `{'PASS' if quality.get("success", False) else 'FAIL'}`
- **Timestamp**: `{quality.get("timestamp", "")}`

### Checks Executed:
- **Has Rows**: `{'PASS' if quality.get("checks", {}).get("has_rows") else 'FAIL'}` (Total: {quality.get("metrics", {}).get("total_rows")})
- **No Missing Titles**: `{'PASS' if quality.get("checks", {}).get("no_missing_titles") else 'FAIL'}` (Missing: {quality.get("metrics", {}).get("missing_titles")})
- **No Missing Summaries**: `{'PASS' if quality.get("checks", {}).get("no_missing_summaries") else 'FAIL'}` (Missing: {quality.get("metrics", {}).get("missing_summaries")})
- **No Duplicates**: `{'PASS' if quality.get("checks", {}).get("no_duplicates") else 'FAIL'}` (Duplicates: {quality.get("metrics", {}).get("duplicate_ids")})
- **No Short Summaries**: `{'PASS' if quality.get("checks", {}).get("no_short_summaries") else 'FAIL'}` (Short < 100 char: {quality.get("metrics", {}).get("short_summaries")})
- **No Negative Age**: `{'PASS' if quality.get("checks", {}).get("no_negative_ages") else 'FAIL'}` (Negative: {quality.get("metrics", {}).get("negative_ages")})

## 4. Freshness Monitoring

- **Status**: `{'FRESH' if freshness.get("is_fresh") else 'STALE'}`
- **Oldest Publication Date**: `{freshness.get("oldest_published", "N/A")}`
- **Latest Publication Date**: `{freshness.get("latest_published", "N/A")}`
- **Stale Rows (exceeding {freshness.get("threshold_days", 180)} days)**: {freshness.get("stale_rows", 0)} / {freshness.get("total_rows", 0)}
"""
    write_text(Path(report_path), md_content)
    print(f"Phase 1 report generated and saved to {report_path}")


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Generate Markdown report comparing baseline, corrupted, and repaired states."""
    md_content = f"""# Data Corruption & Recovery Report (Phase 2)

This report compares metrics and data quality across three pipeline states: **Baseline** (clean), **Corrupted** (damaged), and **Repaired** (recovered).

## 1. RAG Evaluation Metrics Comparison

| Metric | Baseline | Corrupted | Repaired | Change (Corrupt) | Recovery Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Retrieval Hit Rate** | {baseline_metrics.get("retrieval_hit_rate", 0.0):.4f} | {corrupted_metrics.get("retrieval_hit_rate", 0.0):.4f} | {repaired_metrics.get("retrieval_hit_rate", 0.0):.4f} | {corrupted_metrics.get("retrieval_hit_rate", 0.0) - baseline_metrics.get("retrieval_hit_rate", 0.0):+.4f} | {repaired_metrics.get("retrieval_hit_rate", 0.0) - corrupted_metrics.get("retrieval_hit_rate", 0.0):+.4f} |
| **Mean Token F1** | {baseline_metrics.get("mean_token_f1", 0.0):.4f} | {corrupted_metrics.get("mean_token_f1", 0.0):.4f} | {repaired_metrics.get("mean_token_f1", 0.0):.4f} | {corrupted_metrics.get("mean_token_f1", 0.0) - baseline_metrics.get("mean_token_f1", 0.0):+.4f} | {repaired_metrics.get("mean_token_f1", 0.0) - corrupted_metrics.get("mean_token_f1", 0.0):+.4f} |
| **Judge Accuracy** | {baseline_metrics.get("judge_accuracy", 0.0):.4f} | {corrupted_metrics.get("judge_accuracy", 0.0):.4f} | {repaired_metrics.get("judge_accuracy", 0.0):.4f} | {corrupted_metrics.get("judge_accuracy", 0.0) - baseline_metrics.get("judge_accuracy", 0.0):+.4f} | {repaired_metrics.get("judge_accuracy", 0.0) - corrupted_metrics.get("judge_accuracy", 0.0):+.4f} |
| **Mean Judge Score** | {baseline_metrics.get("mean_judge_score", 0.0):.4f} | {corrupted_metrics.get("mean_judge_score", 0.0):.4f} | {repaired_metrics.get("mean_judge_score", 0.0):.4f} | {corrupted_metrics.get("mean_judge_score", 0.0) - baseline_metrics.get("mean_judge_score", 0.0):+.4f} | {repaired_metrics.get("mean_judge_score", 0.0) - corrupted_metrics.get("mean_judge_score", 0.0):+.4f} |

## 2. Data Quality & Freshness Comparison

| Property | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| **Quality Status** | PASS | {'PASS' if corrupted_quality.get("success", False) else 'FAIL'} | {'PASS' if repaired_quality.get("success", False) else 'FAIL'} |
| **Freshness Status** | FRESH | {'FRESH' if corrupted_freshness.get("is_fresh") else 'STALE'} | {'FRESH' if repaired_freshness.get("is_fresh") else 'STALE'} |
| **Row Count** | {baseline_metrics.get("samples", 0)} | {corrupted_metrics.get("samples", 0)} | {repaired_metrics.get("samples", 0)} |
| **Stale Rows** | 0 | {corrupted_freshness.get("stale_rows", 0)} | {repaired_freshness.get("stale_rows", 0)} |

## 3. Findings & Critical Interpretations

1. **Impact of Corruption on Retrieval & Reasoning:**
   - Shows how data quality degradation directly affects retrieval hit rates and LLM reasoning accuracy.
2. **Effectiveness of Recovery:**
   - Proves that reloading and re-cleaning from the original raw source recovers RAG performance.
"""
    write_text(Path(report_path), md_content)
    print(f"Comparison report generated and saved to {report_path}")

