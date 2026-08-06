# =============================================================================
# Author: Quan123781 <quannguyen0442@gmail.com>
# Day 10 lab - Evaluation, Observability, Corruption & Integration
# =============================================================================
from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from core.config import Settings, load_settings
from core.utils import read_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex

METRIC_KEYS = ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")


def require_baseline_artifacts(settings: Settings) -> None:
    """Phase 2 only means something if phase 1 already produced a baseline to compare to."""
    required = {
        "cleaned dataset": settings.paths.clean_json,
        "frozen test set": settings.paths.eval_testset,
        "baseline metrics": settings.paths.baseline_metrics,
        "raw records snapshot": settings.paths.raw_records_json,
    }
    missing = [f"{name} ({path})" for name, path in required.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Baseline artifacts are missing, run script/run_phase1.py first:\n  - "
            + "\n  - ".join(missing)
        )


def save_dataframe(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_json(json_path, orient="records", indent=2)


def evaluation_settings(settings: Settings) -> Settings:
    """Mirror the provider fallback phase 1 uses so both phases are judged the same way."""
    if not settings.google_api_key and settings.openai_api_key:
        print("GOOGLE_API_KEY is empty. Overriding provider to 'openai' for evaluation.")
        return dataclasses.replace(settings, llm_provider="openai", model_name="gpt-4o-mini")
    return settings


def ground_truth_doc_ids(test_set_path: Path) -> list[str]:
    test_set = read_json(test_set_path)
    return sorted({doc_id for item in test_set for doc_id in item["ground_truth_doc_ids"]})


def main() -> None:
    print("Loading settings...")
    settings = load_settings()
    require_baseline_artifacts(settings)

    eval_settings = evaluation_settings(settings)
    test_set_path = settings.paths.eval_testset
    baseline_metrics = read_json(settings.paths.baseline_metrics)

    # 1. Load the cleaned baseline dataset. The JSON snapshot keeps list columns intact,
    #    which the CSV round-trip would flatten into strings.
    baseline_df = pd.DataFrame(read_json(settings.paths.clean_json))
    print(f"Loaded baseline cleaned dataset: {len(baseline_df)} rows")

    targets = ground_truth_doc_ids(test_set_path)
    print(f"Frozen test set references {len(targets)} distinct ground-truth papers")

    # 2. Corrupt the cleaned data on purpose, writing the log next to the metrics.
    print("\n=== Corrupting cleaned dataset ===")
    corrupted_df = corrupt_clean_dataframe(
        baseline_df,
        settings.paths.corruption_log,
        target_paper_ids=targets,
    )
    save_dataframe(
        corrupted_df,
        settings.paths.corrupted_clean_csv,
        settings.paths.corrupted_clean_json,
    )
    print(f"Corrupted dataset saved to {settings.paths.corrupted_clean_csv}")

    # 3. Rebuild the index into its own collection so the baseline stays readable.
    print("\n=== Rebuilding index on corrupted data ===")
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings, settings.paths.corrupted_embeddings_json
    )
    print(f"Index built with collection: {corrupted_index.collection_name}")

    # 4. Evaluate with the same frozen test set: the data is the only variable.
    print("\n=== Evaluating corrupted state ===")
    corrupted_bundle = evaluate_pipeline(
        settings=eval_settings,
        index=corrupted_index,
        test_set_path=test_set_path,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    print(f"Corrupted metrics: {corrupted_bundle.summary}")

    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted_quality")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, settings.paths.quality_dir / "freshness_report_corrupted.json"
    )

    # 5. Repair from the saved raw snapshot, never by re-fetching the source: a fresh fetch
    #    would return a different corpus and make the comparison meaningless.
    print("\n=== Repairing from saved raw records ===")
    records = load_raw_records(settings.paths.raw_records_json)
    print(f"Reloaded {len(records)} raw records from {settings.paths.raw_records_json}")
    repaired_df = build_clean_dataframe(records, datetime.now(UTC))
    save_dataframe(
        repaired_df,
        settings.paths.repaired_clean_csv,
        settings.paths.repaired_clean_json,
    )
    print(f"Repaired dataset saved to {settings.paths.repaired_clean_csv} ({len(repaired_df)} rows)")

    print("\n=== Rebuilding index on repaired data ===")
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, settings.paths.repaired_embeddings_json
    )
    print(f"Index built with collection: {repaired_index.collection_name}")

    print("\n=== Evaluating repaired state ===")
    repaired_bundle = evaluate_pipeline(
        settings=eval_settings,
        index=repaired_index,
        test_set_path=test_set_path,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    print(f"Repaired metrics: {repaired_bundle.summary}")

    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired_quality")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, settings.paths.quality_dir / "freshness_report_repaired.json"
    )

    # 6. Comparison report over the three states.
    print("\n=== Generating comparison report ===")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    print("\n--- Baseline / Corrupted / Repaired ---")
    for key in METRIC_KEYS:
        base = baseline_metrics.get(key)
        bad = corrupted_bundle.summary.get(key)
        fixed = repaired_bundle.summary.get(key)
        print(f"{key:<20} {base:>8.4f} {bad:>10.4f} {fixed:>10.4f}   delta={bad - base:+.4f}")
    print(
        f"{'quality success':<20} {'PASS':>8} "
        f"{('PASS' if corrupted_quality['success'] else 'FAIL'):>10} "
        f"{('PASS' if repaired_quality['success'] else 'FAIL'):>10}"
    )
    print(
        f"{'freshness':<20} {'FRESH':>8} "
        f"{('FRESH' if corrupted_freshness['is_fresh'] else 'STALE'):>10} "
        f"{('FRESH' if repaired_freshness['is_fresh'] else 'STALE'):>10}"
    )
    print("\nHoan thanh Corruption Flow (Phase 2)!")


if __name__ == "__main__":
    main()
